"""Logique métier du planificateur de repas.

Ce package est totalement indépendant de l'interface : il peut être utilisé
depuis un script, des tests ou une autre UI que Streamlit.

    mealplanner.models         structures de données du domaine
    mealplanner.foods          base d'aliments (macros + micronutriments)
    mealplanner.recipes        recettes de base, macros dérivées des aliments
    mealplanner.nutrition      besoins caloriques, macros et répartition par repas
    mealplanner.pantry         garde-manger, règle FEFO et urgence de péremption
    mealplanner.suggester      moteur de suggestion de plats
    mealplanner.substitutions  remplacement d'un ingrédient manquant
    mealplanner.analytics      détection de carences sur 7 jours glissants
    mealplanner.storage        persistance SQLite locale
"""

from .models import Food, MealLog, NutritionFacts, PantryItem, Profile, Recipe
from .storage import Store

__all__ = [
    "Food",
    "MealLog",
    "NutritionFacts",
    "PantryItem",
    "Profile",
    "Recipe",
    "Store",
]

__version__ = "1.0.0"
