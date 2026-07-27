"""Modèles de données du domaine.

Ce module ne connaît ni Streamlit ni SQLite : il ne contient que des structures
de données pures, réutilisables par la logique métier comme par l'interface.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from datetime import date
from typing import Iterable, Optional

# Ordre canonique des nutriments suivis par l'application.
NUTRIENT_KEYS = (
    "kcal",
    "protein",
    "carbs",
    "fat",
    "fiber",
    "iron",
    "calcium",
    "vitamin_c",
    "magnesium",
    "omega3",
)

NUTRIENT_LABELS = {
    "kcal": "Calories",
    "protein": "Protéines",
    "carbs": "Glucides",
    "fat": "Lipides",
    "fiber": "Fibres",
    "iron": "Fer",
    "calcium": "Calcium",
    "vitamin_c": "Vitamine C",
    "magnesium": "Magnésium",
    "omega3": "Oméga-3 (ALA)",
}

NUTRIENT_UNITS = {
    "kcal": "kcal",
    "protein": "g",
    "carbs": "g",
    "fat": "g",
    "fiber": "g",
    "iron": "mg",
    "calcium": "mg",
    "vitamin_c": "mg",
    "magnesium": "mg",
    "omega3": "g",
}

MACRO_KEYS = ("protein", "carbs", "fat")
MICRO_KEYS = ("fiber", "iron", "calcium", "vitamin_c", "magnesium", "omega3")


@dataclass(frozen=True)
class NutritionFacts:
    """Valeurs nutritionnelles agrégeables (additionnables et multipliables)."""

    kcal: float = 0.0
    protein: float = 0.0
    carbs: float = 0.0
    fat: float = 0.0
    fiber: float = 0.0
    iron: float = 0.0
    calcium: float = 0.0
    vitamin_c: float = 0.0
    magnesium: float = 0.0
    omega3: float = 0.0

    def __add__(self, other: "NutritionFacts") -> "NutritionFacts":
        return NutritionFacts(
            **{k: getattr(self, k) + getattr(other, k) for k in NUTRIENT_KEYS}
        )

    def __mul__(self, factor: float) -> "NutritionFacts":
        return NutritionFacts(**{k: getattr(self, k) * factor for k in NUTRIENT_KEYS})

    __rmul__ = __mul__

    def __sub__(self, other: "NutritionFacts") -> "NutritionFacts":
        return NutritionFacts(
            **{k: getattr(self, k) - getattr(other, k) for k in NUTRIENT_KEYS}
        )

    def rounded(self, digits: int = 1) -> "NutritionFacts":
        return NutritionFacts(
            **{k: round(getattr(self, k), digits) for k in NUTRIENT_KEYS}
        )

    def as_dict(self) -> dict[str, float]:
        return {k: getattr(self, k) for k in NUTRIENT_KEYS}

    @classmethod
    def from_dict(cls, data: dict) -> "NutritionFacts":
        return cls(**{k: float(data.get(k, 0.0) or 0.0) for k in NUTRIENT_KEYS})

    @classmethod
    def sum(cls, items: Iterable["NutritionFacts"]) -> "NutritionFacts":
        total = cls()
        for item in items:
            total = total + item
        return total


@dataclass(frozen=True)
class Food:
    """Un aliment de la base, avec ses valeurs pour 100 g (ou 100 ml)."""

    id: str
    name: str
    category: str
    per100g: NutritionFacts
    # Poids indicatif d'une unité usuelle (1 œuf, 1 tortilla...) pour aider la saisie.
    unit_grams: Optional[float] = None
    unit_label: Optional[str] = None

    def facts_for(self, grams: float) -> NutritionFacts:
        return self.per100g * (grams / 100.0)


@dataclass(frozen=True)
class RecipeIngredient:
    food_id: str
    grams: float
    # Un ingrédient « optionnel » (assaisonnement, garniture) ne pénalise pas
    # une recette lorsqu'il manque au garde-manger.
    optional: bool = False


@dataclass(frozen=True)
class Recipe:
    id: str
    name: str
    meals: tuple[str, ...]
    ingredients: tuple[RecipeIngredient, ...]
    steps: tuple[str, ...]
    prep_minutes: int
    tags: tuple[str, ...] = ()


@dataclass
class Profile:
    """Profil utilisateur : tout ce dont dépend le calcul des besoins."""

    weight_kg: float = 75.0
    height_cm: float = 178.0
    age: int = 30
    sex: str = "homme"  # "homme" | "femme"
    activity: str = "modere"  # clé de nutrition.ACTIVITY_LEVELS
    goal: str = "maintien_sportif"  # clé de nutrition.GOALS
    meals_per_day: int = 4

    def as_dict(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    @classmethod
    def from_dict(cls, data: dict) -> "Profile":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    def with_(self, **kwargs) -> "Profile":
        return replace(self, **kwargs)


@dataclass
class PantryItem:
    """Un lot d'aliment présent chez l'utilisateur."""

    food_id: str
    grams: float
    expiry: Optional[date] = None
    id: Optional[int] = None

    def days_left(self, today: Optional[date] = None) -> Optional[int]:
        if self.expiry is None:
            return None
        return (self.expiry - (today or date.today())).days


@dataclass
class MealLog:
    """Un repas effectivement consommé."""

    day: date
    meal: str
    label: str
    facts: NutritionFacts
    recipe_id: Optional[str] = None
    portions: float = 1.0
    id: Optional[int] = None
