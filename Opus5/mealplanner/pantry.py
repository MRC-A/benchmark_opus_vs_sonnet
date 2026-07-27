"""Gestion du garde-manger et de la péremption.

Un même aliment peut exister en plusieurs lots avec des dates de péremption
différentes. Les lots sont donc consommés selon la règle « premier périmé,
premier sorti » (FEFO), et chaque lot porte un score d'urgence continu qui
alimente le moteur de suggestion.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, Optional

from .foods import food_name
from .models import PantryItem

# Horizon au-delà duquel un aliment n'est plus considéré comme « urgent ».
URGENCY_HORIZON_DAYS = 7
# En dessous de ce nombre de jours, on alerte visuellement l'utilisateur.
WARNING_DAYS = 3


def urgency_score(days_left: Optional[int]) -> float:
    """Urgence d'un lot, entre 0 (pas pressé) et 1 (à consommer aujourd'hui).

    Un lot sans date renseignée vaut 0 : ne rien savoir ne doit jamais
    pénaliser ni avantager une recette.
    """
    if days_left is None:
        return 0.0
    if days_left <= 0:
        return 1.0
    if days_left >= URGENCY_HORIZON_DAYS:
        return 0.0
    return (URGENCY_HORIZON_DAYS - days_left) / URGENCY_HORIZON_DAYS


@dataclass(frozen=True)
class Lot:
    """Un lot consommable, enrichi de son urgence."""

    item_id: Optional[int]
    food_id: str
    grams: float
    expiry: Optional[date]
    days_left: Optional[int]
    urgency: float

    @property
    def expired(self) -> bool:
        return self.days_left is not None and self.days_left < 0

    @property
    def critical(self) -> bool:
        return self.days_left is not None and 0 <= self.days_left <= WARNING_DAYS


def build_lots(
    items: Iterable[PantryItem],
    today: Optional[date] = None,
    include_expired: bool = False,
) -> list[Lot]:
    """Convertit les lignes du garde-manger en lots triés par urgence (FEFO)."""
    today = today or date.today()
    lots: list[Lot] = []
    for item in items:
        if item.grams <= 0:
            continue
        days_left = item.days_left(today)
        lot = Lot(
            item_id=item.id,
            food_id=item.food_id,
            grams=float(item.grams),
            expiry=item.expiry,
            days_left=days_left,
            urgency=urgency_score(days_left),
        )
        if lot.expired and not include_expired:
            continue
        lots.append(lot)
    # Les lots datés et les plus proches de la péremption d'abord.
    lots.sort(key=lambda lot: (lot.days_left is None, lot.days_left or 0))
    return lots


def available_grams(lots: Iterable[Lot]) -> dict[str, float]:
    """Quantité totale disponible par aliment."""
    totals: dict[str, float] = {}
    for lot in lots:
        totals[lot.food_id] = totals.get(lot.food_id, 0.0) + lot.grams
    return totals


@dataclass(frozen=True)
class Draw:
    """Résultat d'un prélèvement FEFO sur le garde-manger."""

    food_id: str
    taken: float
    missing: float
    # Urgence moyenne pondérée des lots réellement utilisés.
    urgency: float
    soonest_days_left: Optional[int]

    @property
    def covered(self) -> bool:
        return self.missing <= 1e-6


def draw(lots: Iterable[Lot], food_id: str, grams: float) -> Draw:
    """Simule le prélèvement de `grams` d'un aliment, du plus périssable au moins.

    Ne modifie rien : le moteur de suggestion évalue plusieurs scénarios avant
    que l'utilisateur ne valide quoi que ce soit.
    """
    remaining = float(grams)
    weighted_urgency = 0.0
    taken_total = 0.0
    soonest: Optional[int] = None

    for lot in lots:
        if lot.food_id != food_id or remaining <= 0:
            continue
        taken = min(lot.grams, remaining)
        remaining -= taken
        taken_total += taken
        weighted_urgency += lot.urgency * taken
        if lot.days_left is not None and (soonest is None or lot.days_left < soonest):
            soonest = lot.days_left

    urgency = weighted_urgency / taken_total if taken_total > 0 else 0.0
    return Draw(
        food_id=food_id,
        taken=taken_total,
        missing=max(remaining, 0.0),
        urgency=urgency,
        soonest_days_left=soonest,
    )


def expiring_soon(lots: Iterable[Lot], within_days: int = WARNING_DAYS) -> list[Lot]:
    """Lots à consommer en priorité, triés du plus urgent au moins urgent."""
    selected = [
        lot for lot in lots
        if lot.days_left is not None and lot.days_left <= within_days
    ]
    selected.sort(key=lambda lot: lot.days_left or 0)
    return selected


def describe_lot(lot: Lot) -> str:
    name = food_name(lot.food_id)
    if lot.days_left is None:
        return f"{name} — {lot.grams:.0f} g"
    if lot.days_left < 0:
        return f"{name} — {lot.grams:.0f} g (périmé depuis {-lot.days_left} j)"
    if lot.days_left == 0:
        return f"{name} — {lot.grams:.0f} g (périme aujourd'hui)"
    if lot.days_left == 1:
        return f"{name} — {lot.grams:.0f} g (périme demain)"
    return f"{name} — {lot.grams:.0f} g (dans {lot.days_left} j)"
