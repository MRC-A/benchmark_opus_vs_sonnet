"""Persistance locale (SQLite, fichier unique).

SQLite est retenu plutôt qu'un fichier JSON parce que l'historique des repas est
naturellement relationnel et interrogé par plage de dates (fenêtre glissante de
7 jours) : la base fait ce filtrage nativement, reste cohérente en cas de
fermeture brutale, et ne coûte aucune dépendance (module `sqlite3` de la
bibliothèque standard). Le tout tient dans un seul fichier, facile à sauvegarder
ou à supprimer.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Iterator, Optional, Sequence

from .models import MealLog, NutritionFacts, PantryItem, Profile

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "mealplanner.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS profile (
    id      INTEGER PRIMARY KEY CHECK (id = 1),
    payload TEXT NOT NULL,
    updated TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pantry_items (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    food_id TEXT    NOT NULL,
    grams   REAL    NOT NULL,
    expiry  TEXT,
    added   TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS meal_logs (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    day       TEXT    NOT NULL,
    meal      TEXT    NOT NULL,
    label     TEXT    NOT NULL,
    recipe_id TEXT,
    portions  REAL    NOT NULL DEFAULT 1.0,
    facts     TEXT    NOT NULL,
    created   TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_meal_logs_day ON meal_logs(day);
CREATE INDEX IF NOT EXISTS idx_pantry_expiry ON pantry_items(expiry);
"""


def _to_iso(value: Optional[date]) -> Optional[str]:
    return value.isoformat() if value else None


def _from_iso(value: Optional[str]) -> Optional[date]:
    return date.fromisoformat(value) if value else None


class Store:
    """Point d'entrée unique de la persistance.

    Aucune autre couche ne parle SQL : la logique métier manipule uniquement les
    objets de `models.py`.
    """

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._memory_conn: Optional[sqlite3.Connection] = None
        if str(self.db_path) == ":memory:":
            self._memory_conn = sqlite3.connect(":memory:")
            self._memory_conn.row_factory = sqlite3.Row
        self._init_schema()

    # -- infrastructure ---------------------------------------------------- #

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        if self._memory_conn is not None:
            yield self._memory_conn
            self._memory_conn.commit()
            return
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    # -- profil ------------------------------------------------------------ #

    def load_profile(self) -> Optional[Profile]:
        with self._connect() as conn:
            row = conn.execute("SELECT payload FROM profile WHERE id = 1").fetchone()
        if row is None:
            return None
        return Profile.from_dict(json.loads(row["payload"]))

    def save_profile(self, profile: Profile) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO profile (id, payload, updated) VALUES (1, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET payload = excluded.payload, "
                "updated = excluded.updated",
                (json.dumps(profile.as_dict()), datetime.now().isoformat(timespec="seconds")),
            )

    # -- garde-manger ------------------------------------------------------ #

    def list_pantry(self) -> list[PantryItem]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, food_id, grams, expiry FROM pantry_items "
                "WHERE grams > 0 ORDER BY expiry IS NULL, expiry, id"
            ).fetchall()
        return [
            PantryItem(
                id=row["id"],
                food_id=row["food_id"],
                grams=row["grams"],
                expiry=_from_iso(row["expiry"]),
            )
            for row in rows
        ]

    def add_pantry_item(self, food_id: str, grams: float, expiry: Optional[date] = None) -> int:
        """Ajoute un lot. Deux lots de même aliment et même date sont fusionnés."""
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT id, grams FROM pantry_items WHERE food_id = ? AND "
                "IFNULL(expiry, '') = IFNULL(?, '')",
                (food_id, _to_iso(expiry)),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE pantry_items SET grams = ? WHERE id = ?",
                    (existing["grams"] + grams, existing["id"]),
                )
                return int(existing["id"])
            cursor = conn.execute(
                "INSERT INTO pantry_items (food_id, grams, expiry, added) VALUES (?, ?, ?, ?)",
                (food_id, float(grams), _to_iso(expiry), date.today().isoformat()),
            )
            return int(cursor.lastrowid)

    def update_pantry_item(
        self, item_id: int, grams: float, expiry: Optional[date] = None
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE pantry_items SET grams = ?, expiry = ? WHERE id = ?",
                (float(grams), _to_iso(expiry), item_id),
            )

    def delete_pantry_item(self, item_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM pantry_items WHERE id = ?", (item_id,))

    def clear_pantry(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM pantry_items")

    def consume(self, consumption: Sequence[tuple[str, float]]) -> None:
        """Retire des quantités du garde-manger, du lot le plus périssable au moins.

        Applique la même règle FEFO que le moteur de suggestion, pour que ce qui
        est réellement décompté corresponde à ce qui a été proposé.
        """
        with self._connect() as conn:
            for food_id, grams in consumption:
                remaining = float(grams)
                rows = conn.execute(
                    "SELECT id, grams FROM pantry_items WHERE food_id = ? AND grams > 0 "
                    "ORDER BY expiry IS NULL, expiry, id",
                    (food_id,),
                ).fetchall()
                for row in rows:
                    if remaining <= 0:
                        break
                    taken = min(row["grams"], remaining)
                    remaining -= taken
                    left = row["grams"] - taken
                    if left <= 0.01:
                        conn.execute("DELETE FROM pantry_items WHERE id = ?", (row["id"],))
                    else:
                        conn.execute(
                            "UPDATE pantry_items SET grams = ? WHERE id = ?",
                            (left, row["id"]),
                        )

    def purge_expired(self, today: Optional[date] = None) -> int:
        today = today or date.today()
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM pantry_items WHERE expiry IS NOT NULL AND expiry < ?",
                (today.isoformat(),),
            )
            return cursor.rowcount

    # -- historique des repas ---------------------------------------------- #

    def add_log(self, log: MealLog) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO meal_logs (day, meal, label, recipe_id, portions, facts, created) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    log.day.isoformat(),
                    log.meal,
                    log.label,
                    log.recipe_id,
                    float(log.portions),
                    json.dumps(log.facts.as_dict()),
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
            return int(cursor.lastrowid)

    def delete_log(self, log_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM meal_logs WHERE id = ?", (log_id,))

    def list_logs(
        self, start: Optional[date] = None, end: Optional[date] = None
    ) -> list[MealLog]:
        query = "SELECT id, day, meal, label, recipe_id, portions, facts FROM meal_logs"
        clauses, params = [], []
        if start:
            clauses.append("day >= ?")
            params.append(start.isoformat())
        if end:
            clauses.append("day <= ?")
            params.append(end.isoformat())
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY day DESC, id DESC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            MealLog(
                id=row["id"],
                day=date.fromisoformat(row["day"]),
                meal=row["meal"],
                label=row["label"],
                recipe_id=row["recipe_id"],
                portions=row["portions"],
                facts=NutritionFacts.from_dict(json.loads(row["facts"])),
            )
            for row in rows
        ]

    def logs_for_day(self, day: date) -> list[MealLog]:
        return self.list_logs(start=day, end=day)

    def recent_recipe_ids(self, since: date) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT recipe_id FROM meal_logs "
                "WHERE recipe_id IS NOT NULL AND day >= ?",
                (since.isoformat(),),
            ).fetchall()
        return [row["recipe_id"] for row in rows]

    def reset(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                "DELETE FROM meal_logs; DELETE FROM pantry_items; DELETE FROM profile;"
            )
