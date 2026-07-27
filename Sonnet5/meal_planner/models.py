"""Structures de données du domaine métier."""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


SEXES = ("Homme", "Femme")

ACTIVITY_LEVELS = (
    "Sédentaire (peu ou pas de sport)",
    "Légèrement actif (1-3 séances/semaine)",
    "Modérément actif (3-5 séances/semaine)",
    "Très actif (6-7 séances/semaine)",
    "Extrêmement actif (sport intensif quotidien / métier physique)",
)

GOALS = (
    "Sédentaire - maintien",
    "Sportif - prise de masse",
    "Sportif - sèche",
    "Sportif - maintien",
)

MEAL_TYPES = ("petit_dejeuner", "dejeuner", "diner", "collation")

MEAL_LABELS = {
    "petit_dejeuner": "Petit-déjeuner",
    "dejeuner": "Déjeuner",
    "diner": "Dîner",
    "collation": "Collation",
}


@dataclass
class UserProfile:
    weight_kg: float
    height_cm: float
    age: int
    sex: str
    activity_level: str
    goal: str


@dataclass
class FoodItem:
    name: str
    quantity_g: float
    expiration_date: Optional[date] = None
    id: Optional[int] = None


@dataclass
class Recipe:
    name: str
    meal_types: list
    ingredients: dict  # nom (str) -> quantité en grammes (float)
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float


@dataclass
class MealLogEntry:
    log_date: date
    meal_type: str
    recipe_name: str
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float
    id: Optional[int] = None
