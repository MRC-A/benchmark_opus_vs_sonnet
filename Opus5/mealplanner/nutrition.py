"""Calcul des besoins énergétiques, des macros et de leur répartition par repas.

Chaîne de calcul :
    profil -> métabolisme de base (Mifflin-St Jeor)
           -> dépense totale (facteur d'activité)
           -> objectif (surplus / déficit)
           -> protéines (g/kg) et lipides (% de l'énergie), glucides = reste
           -> répartition sur les repas de la journée
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import MACRO_KEYS, NutritionFacts, Profile

KCAL_PER_G = {"protein": 4.0, "carbs": 4.0, "fat": 9.0}


@dataclass(frozen=True)
class ActivityLevel:
    label: str
    factor: float
    athlete: bool
    hint: str


ACTIVITY_LEVELS: dict[str, ActivityLevel] = {
    "sedentaire": ActivityLevel(
        "Sédentaire", 1.20, False, "Travail assis, pas de sport structuré."
    ),
    "leger": ActivityLevel(
        "Peu actif", 1.375, False, "Marche quotidienne ou 1 à 2 séances par semaine."
    ),
    "modere": ActivityLevel(
        "Sportif régulier", 1.55, True, "3 à 4 séances par semaine."
    ),
    "intense": ActivityLevel(
        "Sportif intensif", 1.725, True, "5 à 6 séances par semaine."
    ),
    "tres_intense": ActivityLevel(
        "Athlète", 1.90, True, "Deux séances par jour ou métier physique."
    ),
}


@dataclass(frozen=True)
class Goal:
    label: str
    kcal_delta: float  # en fraction de la dépense totale
    protein_g_kg: float
    fat_ratio: float  # part de l'énergie apportée par les lipides
    athlete: bool
    hint: str


# Deux jeux d'objectifs bien distincts : un profil sédentaire ne se voit jamais
# proposer 2,4 g/kg de protéines, un profil sportif jamais 1,0 g/kg.
GOALS: dict[str, Goal] = {
    # --- profils sportifs ---
    "prise_de_masse": Goal(
        "Prise de masse", +0.15, 2.0, 0.25, True,
        "Surplus maîtrisé de 15% et glucides élevés pour soutenir l'entraînement.",
    ),
    "seche": Goal(
        "Sèche", -0.20, 2.4, 0.25, True,
        "Déficit de 20% avec protéines très hautes pour préserver la masse maigre.",
    ),
    "maintien_sportif": Goal(
        "Maintien / performance", 0.0, 1.8, 0.28, True,
        "Énergie à l'équilibre, protéines suffisantes pour la récupération.",
    ),
    # --- profils non sportifs ---
    "perte_de_poids": Goal(
        "Perte de poids", -0.18, 1.6, 0.30, False,
        "Déficit modéré, protéines rehaussées pour limiter la fonte musculaire.",
    ),
    "maintien": Goal(
        "Maintien du poids", 0.0, 1.0, 0.33, False,
        "Répartition équilibrée proche des repères de santé publique.",
    ),
    "prise_de_poids": Goal(
        "Prise de poids", +0.12, 1.2, 0.32, False,
        "Léger surplus, densité énergétique augmentée.",
    ),
}

# Bornes de sécurité appliquées après calcul.
MIN_FAT_G_PER_KG = 0.8
MAX_PROTEIN_KCAL_RATIO = 0.40
MIN_CARB_KCAL_RATIO = 0.10


def is_athlete(activity: str) -> bool:
    return ACTIVITY_LEVELS[activity].athlete


def goals_for(activity: str) -> dict[str, Goal]:
    """Objectifs proposables pour un niveau d'activité donné."""
    athlete = is_athlete(activity)
    return {key: goal for key, goal in GOALS.items() if goal.athlete == athlete}


def default_goal(activity: str) -> str:
    return "maintien_sportif" if is_athlete(activity) else "maintien"


def bmr(profile: Profile) -> float:
    """Métabolisme de base — équation de Mifflin-St Jeor."""
    base = 10.0 * profile.weight_kg + 6.25 * profile.height_cm - 5.0 * profile.age
    return base + (5.0 if profile.sex == "homme" else -161.0)


def tdee(profile: Profile) -> float:
    """Dépense énergétique totale sur la journée."""
    return bmr(profile) * ACTIVITY_LEVELS[profile.activity].factor


@dataclass(frozen=True)
class DailyTargets:
    """Objectifs journaliers, macros ET micronutriments suivis."""

    kcal: float
    protein: float
    carbs: float
    fat: float
    fiber: float
    iron: float
    calcium: float
    vitamin_c: float
    magnesium: float
    omega3: float
    bmr: float
    tdee: float

    def as_facts(self) -> NutritionFacts:
        return NutritionFacts(
            kcal=self.kcal, protein=self.protein, carbs=self.carbs, fat=self.fat,
            fiber=self.fiber, iron=self.iron, calcium=self.calcium,
            vitamin_c=self.vitamin_c, magnesium=self.magnesium, omega3=self.omega3,
        )


def daily_targets(profile: Profile) -> DailyTargets:
    """Besoins journaliers complets pour un profil."""
    goal = GOALS[profile.goal]
    base_expenditure = tdee(profile)
    kcal = base_expenditure * (1.0 + goal.kcal_delta)

    # 1. Protéines : ancrées sur le poids de corps, jamais sur un pourcentage.
    protein = goal.protein_g_kg * profile.weight_kg
    if protein * KCAL_PER_G["protein"] > kcal * MAX_PROTEIN_KCAL_RATIO:
        protein = kcal * MAX_PROTEIN_KCAL_RATIO / KCAL_PER_G["protein"]

    # 2. Lipides : part de l'énergie, avec un plancher hormonal en g/kg.
    fat = kcal * goal.fat_ratio / KCAL_PER_G["fat"]
    fat = max(fat, MIN_FAT_G_PER_KG * profile.weight_kg)

    # 3. Glucides : le reste. Si le reste est trop faible, on rogne les lipides.
    remaining = kcal - protein * KCAL_PER_G["protein"] - fat * KCAL_PER_G["fat"]
    min_carb_kcal = kcal * MIN_CARB_KCAL_RATIO
    if remaining < min_carb_kcal:
        deficit = min_carb_kcal - remaining
        fat = max(fat - deficit / KCAL_PER_G["fat"], MIN_FAT_G_PER_KG * profile.weight_kg * 0.75)
        remaining = kcal - protein * KCAL_PER_G["protein"] - fat * KCAL_PER_G["fat"]
    carbs = max(remaining, 0.0) / KCAL_PER_G["carbs"]

    # L'énergie affichée est recalculée depuis les macros retenues : ce que
    # l'utilisateur voit est exactement ce que la somme des repas donnera.
    kcal = protein * 4.0 + carbs * 4.0 + fat * 9.0

    female = profile.sex == "femme"
    return DailyTargets(
        kcal=kcal,
        protein=protein,
        carbs=carbs,
        fat=fat,
        # Fibres : 14 g pour 1000 kcal, avec un plancher de 25 g.
        fiber=max(25.0, 14.0 * kcal / 1000.0),
        iron=16.0 if (female and profile.age < 51) else 11.0,
        calcium=1000.0 if profile.age >= 25 else 1200.0,
        vitamin_c=110.0,
        magnesium=300.0 if female else 380.0,
        # ALA : environ 1% de l'apport énergétique total.
        omega3=max(1.6, kcal * 0.01 / 9.0),
        bmr=bmr(profile),
        tdee=base_expenditure,
    )


# --------------------------------------------------------------------------- #
# Répartition sur la journée
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class MealSlot:
    key: str
    label: str
    # Poids relatifs, macro par macro (normalisés ensuite sur la journée).
    protein: float
    carbs: float
    fat: float


# Les glucides sont concentrés le matin et autour de l'entraînement, les lipides
# décalés vers le soir, les protéines réparties de façon plus homogène (la
# synthèse protéique répond mieux à des apports réguliers).
MEAL_PLANS: dict[int, tuple[MealSlot, ...]] = {
    3: (
        MealSlot("petit_dej", "Petit-déjeuner", 24, 32, 22),
        MealSlot("dejeuner", "Déjeuner", 40, 40, 40),
        MealSlot("diner", "Dîner", 36, 28, 38),
    ),
    4: (
        MealSlot("petit_dej", "Petit-déjeuner", 22, 28, 22),
        MealSlot("dejeuner", "Déjeuner", 33, 32, 34),
        MealSlot("collation", "Collation", 17, 20, 12),
        MealSlot("diner", "Dîner", 28, 20, 32),
    ),
    5: (
        MealSlot("petit_dej", "Petit-déjeuner", 20, 24, 20),
        MealSlot("collation_matin", "Collation du matin", 11, 11, 9),
        MealSlot("dejeuner", "Déjeuner", 29, 29, 30),
        MealSlot("collation", "Collation", 16, 18, 11),
        MealSlot("diner", "Dîner", 24, 18, 30),
    ),
}

MEAL_LABELS = {
    slot.key: slot.label for plan in MEAL_PLANS.values() for slot in plan
}


@dataclass(frozen=True)
class MealTarget:
    key: str
    label: str
    kcal: float
    protein: float
    carbs: float
    fat: float

    def as_facts(self) -> NutritionFacts:
        return NutritionFacts(
            kcal=self.kcal, protein=self.protein, carbs=self.carbs, fat=self.fat
        )


def split_by_meal(targets: DailyTargets, meals_per_day: int) -> list[MealTarget]:
    """Répartit les macros journalières sur les repas.

    Chaque macro est normalisée indépendamment : la somme des repas redonne
    exactement l'objectif du jour, macro par macro. L'énergie de chaque repas
    est ensuite recalculée depuis ses macros, ce qui garantit la cohérence.
    """
    plan = MEAL_PLANS.get(meals_per_day) or MEAL_PLANS[4]
    totals = {key: sum(getattr(slot, key) for slot in plan) for key in MACRO_KEYS}

    meal_targets: list[MealTarget] = []
    for slot in plan:
        macros = {
            key: getattr(targets, key) * getattr(slot, key) / totals[key]
            for key in MACRO_KEYS
        }
        kcal = sum(macros[key] * KCAL_PER_G[key] for key in MACRO_KEYS)
        meal_targets.append(
            MealTarget(key=slot.key, label=slot.label, kcal=kcal, **macros)
        )
    return meal_targets


def macro_energy_split(targets: DailyTargets) -> dict[str, float]:
    """Part de l'énergie apportée par chaque macro (pour l'affichage)."""
    total = targets.kcal or 1.0
    return {
        key: getattr(targets, key) * KCAL_PER_G[key] / total * 100.0
        for key in MACRO_KEYS
    }
