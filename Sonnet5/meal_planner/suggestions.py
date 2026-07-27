"""Moteur de suggestion de plats.

Combine trois critères, invisibles pour l'utilisateur final qui ne voit
que la liste de suggestions triée :
  1. Faisabilité avec les aliments disponibles (quantité suffisante).
  2. Proximité des macros de la recette avec la cible du repas concerné.
  3. Priorité aux recettes qui utilisent des ingrédients proches de la
     péremption (pour éviter le gaspillage).
"""

from datetime import date

from .substitutions import suggest_substitute

EXPIRATION_HORIZON_DAYS = 14  # au-delà, un aliment n'apporte plus de bonus d'urgence


def _macro_distance(recipe, target_macros: dict) -> float:
    distance = 0.0
    for key in ("calories", "protein_g", "carbs_g", "fat_g"):
        target = target_macros.get(key) or 1
        recipe_value = getattr(recipe, key)
        distance += abs(recipe_value - target) / target
    return distance


def find_matching_food(ingredient_name: str, inventory: list):
    """Retourne l'aliment en stock correspondant au nom demandé, ou None."""
    normalized = ingredient_name.strip().lower()
    for food in inventory:
        if food.name == normalized or normalized in food.name or food.name in normalized:
            return food
    return None


def _evaluate_recipe(recipe, inventory: list, today: date):
    """Analyse une recette face à l'inventaire courant.

    Retourne un dict avec : ingrédients disponibles/manquants, urgence de
    péremption exploitée, et suggestions de substitution pour ce qui manque.
    """
    available = []
    missing = []
    urgency_bonus = 0.0

    for ingredient_name, needed_qty in recipe.ingredients.items():
        food = find_matching_food(ingredient_name, inventory)
        if food is not None and food.quantity_g >= needed_qty:
            available.append(ingredient_name)
            if food.expiration_date is not None:
                days_left = (food.expiration_date - today).days
                if days_left <= EXPIRATION_HORIZON_DAYS:
                    urgency_bonus += max(0, EXPIRATION_HORIZON_DAYS - days_left)
        else:
            substitutes = suggest_substitute(ingredient_name)
            missing.append({"ingredient": ingredient_name, "substitutes": substitutes})

    return {
        "available_ingredients": available,
        "missing_ingredients": missing,
        "urgency_bonus": urgency_bonus,
    }


def suggest_recipes_for_meal(recipes: list, inventory: list, meal_type: str,
                              target_macros: dict, today: date = None, top_n: int = 5):
    """Classe les recettes adaptées à `meal_type` selon faisabilité,
    proximité macro et urgence de péremption des ingrédients disponibles."""
    today = today or date.today()

    candidates = [r for r in recipes if meal_type in r.meal_types]

    scored = []
    for recipe in candidates:
        evaluation = _evaluate_recipe(recipe, inventory, today)
        macro_distance = _macro_distance(recipe, target_macros)
        # L'urgence de péremption réduit artificiellement la distance :
        # une recette qui sauve des aliments qui périment remonte dans le classement.
        adjusted_score = macro_distance - (evaluation["urgency_bonus"] * 0.05)
        scored.append({
            "recipe": recipe,
            "missing_ingredients": evaluation["missing_ingredients"],
            "available_ingredients": evaluation["available_ingredients"],
            "can_make_fully": len(evaluation["missing_ingredients"]) == 0,
            "uses_expiring_soon": evaluation["urgency_bonus"] > 0,
            "macro_distance": macro_distance,
            "score": adjusted_score,
        })

    scored.sort(key=lambda s: (len(s["missing_ingredients"]), s["score"]))
    return scored[:top_n]
