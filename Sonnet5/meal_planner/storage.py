"""Couche de persistance locale (SQLite).

Toute l'interface ne connaît que ces méthodes : les détails du schéma
et des requêtes SQL restent internes à ce module.
"""

import os
import sqlite3
from datetime import date, datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "app.db")


def _connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _connect()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            weight_kg REAL NOT NULL,
            height_cm REAL NOT NULL,
            age INTEGER NOT NULL,
            sex TEXT NOT NULL,
            activity_level TEXT NOT NULL,
            goal TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            quantity_g REAL NOT NULL,
            expiration_date TEXT
        );

        CREATE TABLE IF NOT EXISTS meal_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_date TEXT NOT NULL,
            meal_type TEXT NOT NULL,
            recipe_name TEXT NOT NULL,
            calories REAL NOT NULL,
            protein_g REAL NOT NULL,
            carbs_g REAL NOT NULL,
            fat_g REAL NOT NULL,
            fiber_g REAL NOT NULL
        );
        """
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------- Profil ---

def save_profile(profile) -> None:
    conn = _connect()
    conn.execute(
        """
        INSERT INTO profile (id, weight_kg, height_cm, age, sex, activity_level, goal)
        VALUES (1, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            weight_kg=excluded.weight_kg, height_cm=excluded.height_cm,
            age=excluded.age, sex=excluded.sex,
            activity_level=excluded.activity_level, goal=excluded.goal
        """,
        (profile.weight_kg, profile.height_cm, profile.age, profile.sex,
         profile.activity_level, profile.goal),
    )
    conn.commit()
    conn.close()


def get_profile():
    from .models import UserProfile
    conn = _connect()
    row = conn.execute("SELECT * FROM profile WHERE id = 1").fetchone()
    conn.close()
    if row is None:
        return None
    return UserProfile(
        weight_kg=row["weight_kg"], height_cm=row["height_cm"], age=row["age"],
        sex=row["sex"], activity_level=row["activity_level"], goal=row["goal"],
    )


# ------------------------------------------------------------ Aliments -----

def add_food(name: str, quantity_g: float, expiration_date=None) -> None:
    conn = _connect()
    conn.execute(
        "INSERT INTO foods (name, quantity_g, expiration_date) VALUES (?, ?, ?)",
        (name.strip().lower(), quantity_g,
         expiration_date.isoformat() if isinstance(expiration_date, date) else expiration_date),
    )
    conn.commit()
    conn.close()


def update_food_quantity(food_id: int, quantity_g: float) -> None:
    conn = _connect()
    if quantity_g <= 0:
        conn.execute("DELETE FROM foods WHERE id = ?", (food_id,))
    else:
        conn.execute("UPDATE foods SET quantity_g = ? WHERE id = ?", (quantity_g, food_id))
    conn.commit()
    conn.close()


def delete_food(food_id: int) -> None:
    conn = _connect()
    conn.execute("DELETE FROM foods WHERE id = ?", (food_id,))
    conn.commit()
    conn.close()


def get_foods():
    from .models import FoodItem
    conn = _connect()
    rows = conn.execute("SELECT * FROM foods ORDER BY expiration_date IS NULL, expiration_date ASC").fetchall()
    conn.close()
    items = []
    for row in rows:
        exp = None
        if row["expiration_date"]:
            exp = datetime.strptime(row["expiration_date"], "%Y-%m-%d").date()
        items.append(FoodItem(id=row["id"], name=row["name"], quantity_g=row["quantity_g"], expiration_date=exp))
    return items


# ---------------------------------------------------------- Journal repas --

def log_meal(entry) -> None:
    conn = _connect()
    conn.execute(
        """
        INSERT INTO meal_logs (log_date, meal_type, recipe_name, calories, protein_g, carbs_g, fat_g, fiber_g)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (entry.log_date.isoformat(), entry.meal_type, entry.recipe_name, entry.calories,
         entry.protein_g, entry.carbs_g, entry.fat_g, entry.fiber_g),
    )
    conn.commit()
    conn.close()


def get_logs(start_date=None, end_date=None):
    from .models import MealLogEntry
    conn = _connect()
    query = "SELECT * FROM meal_logs"
    params = []
    if start_date and end_date:
        query += " WHERE log_date BETWEEN ? AND ?"
        params = [start_date.isoformat(), end_date.isoformat()]
    query += " ORDER BY log_date DESC, id DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [
        MealLogEntry(
            id=row["id"], log_date=datetime.strptime(row["log_date"], "%Y-%m-%d").date(),
            meal_type=row["meal_type"], recipe_name=row["recipe_name"], calories=row["calories"],
            protein_g=row["protein_g"], carbs_g=row["carbs_g"], fat_g=row["fat_g"], fiber_g=row["fiber_g"],
        )
        for row in rows
    ]
