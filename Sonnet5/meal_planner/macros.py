"""Calcul des besoins caloriques, de la répartition des macronutriments
et de leur distribution intelligente sur les repas de la journée.

Toute la complexité (formules, coefficients, pondération par repas) est
volontairement isolée ici : l'interface ne manipule que le résultat final.
"""

from .models import MEAL_TYPES

ACTIVITY_MULTIPLIERS = {
    "Sédentaire (peu ou pas de sport)": 1.2,
    "Légèrement actif (1-3 séances/semaine)": 1.375,
    "Modérément actif (3-5 séances/semaine)": 1.55,
    "Très actif (6-7 séances/semaine)": 1.725,
    "Extrêmement actif (sport intensif quotidien / métier physique)": 1.9,
}

# Ajustement calorique et cible protéique (g/kg de poids de corps) par objectif.
# C'est ici que le profil "sportif" (musculation) se distingue clairement
# du profil "sédentaire" : objectifs caloriques et besoins en protéines
# nettement plus élevés et orientés performance/composition corporelle.
GOAL_SETTINGS = {
    "Sédentaire - maintien": {
        "calorie_factor": 1.0,
        "protein_per_kg": 1.0,
        "fat_ratio": 0.30,
    },
    "Sportif - prise de masse": {
        "calorie_factor": 1.15,
        "protein_per_kg": 2.0,
        "fat_ratio": 0.25,
    },
    "Sportif - sèche": {
        "calorie_factor": 0.80,
        "protein_per_kg": 2.2,
        "fat_ratio": 0.25,
    },
    "Sportif - maintien": {
        "calorie_factor": 1.0,
        "protein_per_kg": 1.8,
        "fat_ratio": 0.25,
    },
}

# Répartition des macros par repas. Les colonnes somment à 1.0 sur la
# journée pour chaque macro, mais les proportions diffèrent par macro
# (ex: plus de glucides au petit-déjeuner/déjeuner, plus de protéines
# réparties largement, un peu plus de lipides le soir) plutôt qu'un
# simple partage uniforme des calories totales.
MEAL_DISTRIBUTION = {
    "petit_dejeuner": {"calories": 0.25, "protein_g": 0.20, "carbs_g": 0.30, "fat_g": 0.25},
    "dejeuner": {"calories": 0.35, "protein_g": 0.35, "carbs_g": 0.35, "fat_g": 0.30},
    "diner": {"calories": 0.30, "protein_g": 0.35, "carbs_g": 0.25, "fat_g": 0.35},
    "collation": {"calories": 0.10, "protein_g": 0.10, "carbs_g": 0.10, "fat_g": 0.10},
}

FIBER_PER_1000_KCAL = 14.0  # recommandation nutritionnelle standard


def calculate_bmr(weight_kg: float, height_cm: float, age: int, sex: str) -> float:
    """Métabolisme de base (formule de Mifflin-St Jeor)."""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if sex == "Homme" else base - 161


def calculate_tdee(bmr: float, activity_level: str) -> float:
    return bmr * ACTIVITY_MULTIPLIERS[activity_level]


def calculate_daily_macros(profile) -> dict:
    """Retourne les calories et macros cibles pour la journée entière,
    en fonction du profil complet (physique + objectif)."""
    bmr = calculate_bmr(profile.weight_kg, profile.height_cm, profile.age, profile.sex)
    tdee = calculate_tdee(bmr, profile.activity_level)

    settings = GOAL_SETTINGS[profile.goal]
    calories = tdee * settings["calorie_factor"]

    protein_g = settings["protein_per_kg"] * profile.weight_kg
    fat_g = (calories * settings["fat_ratio"]) / 9
    protein_kcal = protein_g * 4
    fat_kcal = fat_g * 9
    carbs_kcal = max(calories - protein_kcal - fat_kcal, 0)
    carbs_g = carbs_kcal / 4

    fiber_g = (calories / 1000) * FIBER_PER_1000_KCAL

    return {
        "calories": round(calories),
        "protein_g": round(protein_g),
        "carbs_g": round(carbs_g),
        "fat_g": round(fat_g),
        "fiber_g": round(fiber_g),
    }


def distribute_macros_by_meal(daily_macros: dict) -> dict:
    """Éclate les macros/calories journaliers par repas selon
    MEAL_DISTRIBUTION. Retourne {meal_type: {calories, protein_g, ...}}."""
    result = {}
    for meal_type in MEAL_TYPES:
        ratios = MEAL_DISTRIBUTION[meal_type]
        result[meal_type] = {
            "calories": round(daily_macros["calories"] * ratios["calories"]),
            "protein_g": round(daily_macros["protein_g"] * ratios["protein_g"]),
            "carbs_g": round(daily_macros["carbs_g"] * ratios["carbs_g"]),
            "fat_g": round(daily_macros["fat_g"] * ratios["fat_g"]),
        }
    return result
