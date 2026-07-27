"""Moteur de suggestion de plats.

Pour un repas donné, on cherche le couple (recette, taille de portion) qui
maximise un score composite :

    score = 0.50 · adéquation macros
          + 0.28 · couverture par le garde-manger
          + 0.22 · urgence de péremption des ingrédients utilisés
          − pénalité de répétition récente

La taille de portion est explorée par balayage (0,5 à 2,0 par pas de 0,05) :
c'est exact sur un espace aussi petit, sans dépendance à un solveur, et cela
permet de tenir compte du fait que la couverture du garde-manger dépend
elle-même de la portion retenue.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, Optional, Sequence

from .foods import get_food
from .models import Food, NutritionFacts, Recipe
from .pantry import Draw, Lot, available_grams, draw
from .recipes import RECIPES, recipe_facts, recipes_for_meal
from .substitutions import Substitution, suggest_substitute

# Pondérations du score composite.
W_FIT = 0.50
W_COVERAGE = 0.28
W_URGENCY = 0.22
# Malus appliqué à une recette déjà consommée très récemment.
REPEAT_PENALTY = 0.10

PORTION_MIN, PORTION_MAX, PORTION_STEP = 0.5, 2.0, 0.05

# Poids relatifs dans le calcul de l'écart aux macros cibles.
_FIT_WEIGHTS = {"kcal": 1.0, "protein": 1.3, "carbs": 0.8, "fat": 0.8}


@dataclass(frozen=True)
class IngredientPlan:
    food: Food
    grams: float
    from_pantry: float
    missing: float
    days_left: Optional[int]
    urgency: float
    optional: bool
    substitution: Optional[Substitution] = None

    @property
    def covered(self) -> bool:
        return self.missing <= 1e-6


@dataclass
class Suggestion:
    recipe: Recipe
    portions: float
    facts: NutritionFacts
    target: NutritionFacts
    ingredients: list[IngredientPlan]
    score: float
    fit: float
    coverage: float
    urgency: float
    notes: list[str] = field(default_factory=list)

    @property
    def missing(self) -> list[IngredientPlan]:
        return [ing for ing in self.ingredients if not ing.covered]

    @property
    def priority_ingredients(self) -> list[IngredientPlan]:
        """Ingrédients retenus parce qu'ils périment bientôt."""
        urgent = [ing for ing in self.ingredients if ing.urgency > 0 and ing.from_pantry > 0]
        urgent.sort(key=lambda ing: ing.days_left if ing.days_left is not None else 99)
        return urgent

    @property
    def cookable_now(self) -> bool:
        return all(ing.covered or ing.optional for ing in self.ingredients)

    def delta(self) -> NutritionFacts:
        return self.facts - self.target


def macro_fit(facts: NutritionFacts, target: NutritionFacts) -> float:
    """Adéquation aux macros cibles, entre 0 et 1 (1 = parfait)."""
    total_weight = 0.0
    total_error = 0.0
    for key, weight in _FIT_WEIGHTS.items():
        goal = getattr(target, key)
        if goal <= 0:
            continue
        error = abs(getattr(facts, key) - goal) / goal
        total_error += weight * min(error, 1.5)
        total_weight += weight
    if total_weight == 0:
        return 0.0
    return max(0.0, 1.0 - total_error / total_weight)


def _ingredient_weights(recipe: Recipe) -> dict[str, float]:
    """Importance relative de chaque ingrédient, pondérée par son énergie.

    Manquer 150 g de poulet doit peser bien plus lourd que manquer 8 g d'huile ;
    la part d'énergie est un proxy simple et stable pour cela. Les ingrédients
    optionnels comptent moitié moins.
    """
    energies: dict[str, float] = {}
    for ing in recipe.ingredients:
        kcal = get_food(ing.food_id).facts_for(ing.grams).kcal
        energies[ing.food_id] = max(kcal, 5.0) * (0.5 if ing.optional else 1.0)
    total = sum(energies.values()) or 1.0
    return {food_id: value / total for food_id, value in energies.items()}


def _evaluate(
    recipe: Recipe,
    portions: float,
    lots: Sequence[Lot],
    weights: dict[str, float],
    base_facts: NutritionFacts,
    target: NutritionFacts,
) -> tuple[float, float, float, float, dict[str, Draw]]:
    """Score d'une recette à une taille de portion donnée."""
    draws: dict[str, Draw] = {}
    coverage = 0.0
    urgency = 0.0

    for ing in recipe.ingredients:
        needed = ing.grams * portions
        result = draw(lots, ing.food_id, needed)
        draws[ing.food_id] = result
        weight = weights[ing.food_id]
        share = result.taken / needed if needed > 0 else 1.0
        coverage += weight * share
        urgency += weight * share * result.urgency

    fit = macro_fit(base_facts * portions, target)
    score = W_FIT * fit + W_COVERAGE * coverage + W_URGENCY * urgency
    return score, fit, coverage, urgency, draws


def _portions_grid() -> list[float]:
    steps = int(round((PORTION_MAX - PORTION_MIN) / PORTION_STEP)) + 1
    return [round(PORTION_MIN + i * PORTION_STEP, 2) for i in range(steps)]


def suggest(
    target: NutritionFacts,
    lots: Sequence[Lot],
    meal_key: str = "dejeuner",
    limit: int = 3,
    recent_recipe_ids: Iterable[str] = (),
    only_cookable: bool = False,
    candidates: Optional[Sequence[Recipe]] = None,
) -> list[Suggestion]:
    """Meilleures propositions de plats pour un repas.

    `target` : macros visées pour ce repas.
    `lots`   : garde-manger disponible (voir `pantry.build_lots`).
    `only_cookable` : ne retenir que les recettes réalisables sans course.
    """
    pool = list(candidates) if candidates is not None else recipes_for_meal(meal_key)
    if not pool:
        pool = list(RECIPES)
    recent = set(recent_recipe_ids)
    stock = available_grams(lots)
    grid = _portions_grid()

    suggestions: list[Suggestion] = []
    for recipe in pool:
        weights = _ingredient_weights(recipe)
        base_facts = recipe_facts(recipe, 1.0)

        best = None
        for portions in grid:
            evaluation = _evaluate(recipe, portions, lots, weights, base_facts, target)
            if best is None or evaluation[0] > best[0]:
                best = (*evaluation, portions)

        score, fit, coverage, urgency, draws, portions = best
        if recipe.id in recent:
            score -= REPEAT_PENALTY

        ingredients: list[IngredientPlan] = []
        # Ce qui reste réellement disponible pour les substitutions : le stock
        # moins ce que la recette consomme déjà, moins les substituts déjà
        # proposés plus haut dans la même recette.
        free_stock = {
            food_id: qty - (draws[food_id].taken if food_id in draws else 0.0)
            for food_id, qty in stock.items()
        }
        for ing in recipe.ingredients:
            food = get_food(ing.food_id)
            result = draws[ing.food_id]
            needed = ing.grams * portions
            substitution = None
            if result.missing > 1e-6:
                substitution = suggest_substitute(
                    ing.food_id, result.missing, free_stock
                )
                if substitution and substitution.in_pantry:
                    key = substitution.replacement.id
                    free_stock[key] = max(0.0, free_stock.get(key, 0.0) - substitution.grams)
            ingredients.append(
                IngredientPlan(
                    food=food,
                    grams=needed,
                    from_pantry=result.taken,
                    missing=result.missing,
                    days_left=result.soonest_days_left,
                    urgency=result.urgency,
                    optional=ing.optional,
                    substitution=substitution,
                )
            )

        suggestion = Suggestion(
            recipe=recipe,
            portions=portions,
            facts=base_facts * portions,
            target=target,
            ingredients=ingredients,
            score=score,
            fit=fit,
            coverage=coverage,
            urgency=urgency,
        )
        suggestion.notes = _build_notes(suggestion, recipe.id in recent)

        if only_cookable and not suggestion.cookable_now:
            continue
        suggestions.append(suggestion)

    suggestions.sort(key=lambda s: s.score, reverse=True)
    return suggestions[:limit]


def _build_notes(suggestion: Suggestion, repeated: bool) -> list[str]:
    notes: list[str] = []
    urgent = suggestion.priority_ingredients
    if urgent:
        top = urgent[0]
        if top.days_left is not None and top.days_left <= 0:
            notes.append(f"Utilise {top.food.name}, à consommer aujourd'hui.")
        elif top.days_left is not None and top.days_left <= 3:
            notes.append(
                f"Utilise {top.food.name}, qui périme dans {top.days_left} jour(s)."
            )
    if suggestion.fit >= 0.9:
        notes.append("Colle très bien aux macros de ce repas.")

    gap = suggestion.facts.kcal - suggestion.target.kcal
    if suggestion.target.kcal > 0 and abs(gap) / suggestion.target.kcal > 0.20:
        if gap < 0:
            notes.append(
                f"Apporte {abs(gap):.0f} kcal de moins que la cible : "
                "complétez avec une portion de féculent ou un fruit."
            )
        else:
            notes.append(
                f"Apporte {gap:.0f} kcal de plus que la cible : "
                "réduisez la portion de féculent si besoin."
            )

    if suggestion.coverage >= 0.999:
        notes.append("Réalisable immédiatement avec ce que vous avez.")
    if repeated:
        notes.append("Déjà consommé récemment — pensez à varier.")
    return notes


def plan_day(
    meal_targets: Sequence,
    lots: Sequence[Lot],
    recent_recipe_ids: Iterable[str] = (),
) -> dict[str, Optional[Suggestion]]:
    """Compose une journée complète en évitant de proposer deux fois le même plat.

    Le garde-manger n'est pas décrémenté entre les repas : l'objectif est de
    proposer une journée cohérente, pas de garantir un stock suffisant.
    """
    used: set[str] = set(recent_recipe_ids)
    plan: dict[str, Optional[Suggestion]] = {}
    for meal in meal_targets:
        options = suggest(
            target=meal.as_facts(),
            lots=lots,
            meal_key=meal.key,
            limit=5,
            recent_recipe_ids=used,
        )
        choice = next((s for s in options if s.recipe.id not in used), None)
        choice = choice or (options[0] if options else None)
        if choice:
            used.add(choice.recipe.id)
        plan[meal.key] = choice
    return plan
