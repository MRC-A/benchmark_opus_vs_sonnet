"""Substitutions d'ingrédients.

Objectif assumé : rester **simple et lisible**. On ne cherche pas à recomposer
les macros à l'identique, mais à proposer un remplacement crédible en cuisine,
avec une quantité ajustée sur le nutriment dominant de l'aliment manquant
(protéines pour une viande, glucides pour un féculent, lipides pour une huile).

Priorité de sélection :
    1. un équivalent « culinaire » explicite déjà présent dans le garde-manger ;
    2. un aliment de la même catégorie présent dans le garde-manger ;
    3. un équivalent explicite, même absent du garde-manger (à acheter).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

from .foods import FOODS, get_food
from .models import Food

# Équivalences culinaires classiques, du plus au moins proche.
EQUIVALENCES: dict[str, tuple[str, ...]] = {
    "poulet_blanc": ("dinde_escalope", "thon_naturel", "blanc_oeuf", "tofu_ferme", "crevettes"),
    "dinde_escalope": ("poulet_blanc", "jambon_blanc", "thon_naturel", "tofu_ferme"),
    "boeuf_hache_5": ("poulet_blanc", "dinde_escalope", "lentilles", "tofu_ferme"),
    "saumon": ("thon_naturel", "crevettes", "oeuf"),
    "thon_naturel": ("saumon", "poulet_blanc", "crevettes", "oeuf"),
    "crevettes": ("thon_naturel", "poulet_blanc"),
    "oeuf": ("blanc_oeuf", "tofu_ferme", "jambon_blanc"),
    "blanc_oeuf": ("oeuf", "fromage_blanc_0", "whey"),
    "jambon_blanc": ("dinde_escalope", "poulet_blanc"),
    "tofu_ferme": ("oeuf", "pois_chiches", "lentilles"),
    "lentilles": ("pois_chiches", "haricots_rouges", "quinoa"),
    "pois_chiches": ("haricots_rouges", "lentilles"),
    "haricots_rouges": ("pois_chiches", "lentilles"),
    "whey": ("fromage_blanc_0", "skyr"),
    "riz_blanc": ("riz_complet", "semoule", "quinoa", "pates"),
    "riz_complet": ("riz_blanc", "quinoa", "pates_completes"),
    "pates": ("pates_completes", "riz_blanc", "semoule"),
    "pates_completes": ("pates", "riz_complet", "quinoa"),
    "quinoa": ("riz_complet", "semoule", "riz_blanc"),
    "semoule": ("riz_blanc", "quinoa", "pates"),
    "flocons_avoine": ("pain_complet", "semoule", "riz_blanc"),
    "pain_complet": ("tortilla_ble_complet", "flocons_avoine"),
    "tortilla_ble_complet": ("pain_complet",),
    "patate_douce": ("pomme_de_terre", "riz_blanc", "semoule"),
    "pomme_de_terre": ("patate_douce", "riz_blanc", "semoule"),
    "brocoli": ("haricots_verts", "courgette", "epinards", "petits_pois"),
    "haricots_verts": ("brocoli", "courgette", "petits_pois"),
    "epinards": ("brocoli", "salade_verte", "courgette"),
    "courgette": ("haricots_verts", "brocoli", "poivron"),
    "poivron": ("tomate", "courgette", "oignon"),
    "tomate": ("poivron", "sauce_tomate", "concombre"),
    "sauce_tomate": ("tomate",),
    "oignon": ("carotte", "poivron"),
    "carotte": ("courgette", "oignon", "petits_pois"),
    "petits_pois": ("haricots_verts", "mais_doux", "brocoli"),
    "salade_verte": ("epinards", "concombre"),
    "concombre": ("courgette", "salade_verte", "tomate"),
    "champignons": ("courgette", "poivron"),
    "mais_doux": ("petits_pois", "riz_blanc"),
    "banane": ("pomme", "myrtilles", "orange"),
    "pomme": ("banane", "orange", "myrtilles"),
    "myrtilles": ("pomme", "banane"),
    "orange": ("pomme", "banane"),
    "skyr": ("fromage_blanc_0", "yaourt_grec"),
    "fromage_blanc_0": ("skyr", "yaourt_grec"),
    "yaourt_grec": ("skyr", "fromage_blanc_0"),
    "lait_demi_ecreme": ("yaourt_grec", "fromage_blanc_0", "skyr"),
    "feta": ("mozzarella", "parmesan"),
    "mozzarella": ("feta", "parmesan"),
    "parmesan": ("feta", "mozzarella"),
    "huile_olive": ("huile_colza", "avocat", "amandes"),
    "huile_colza": ("huile_olive", "noix"),
    "beurre_cacahuete": ("amandes", "noix"),
    "amandes": ("noix", "beurre_cacahuete", "graines_chia"),
    "noix": ("amandes", "graines_chia", "beurre_cacahuete"),
    "graines_chia": ("noix", "amandes"),
    "avocat": ("huile_olive", "amandes"),
    "miel": ("banane", "chocolat_noir_70"),
    "chocolat_noir_70": ("miel", "amandes"),
}

# Nutriment sur lequel on cale la quantité de remplacement, par catégorie.
_ANCHOR_BY_CATEGORY = {
    "proteine_animale": "protein",
    "proteine_vegetale": "protein",
    "feculent": "carbs",
    "matiere_grasse": "fat",
    "laitier": "protein",
    "legume": "kcal",
    "fruit": "carbs",
    "autre": "kcal",
}

# Facteur de conversion accepté pour le repli « même catégorie » : au-delà, la
# substitution devient absurde (500 g de brocoli pour 10 g d'huile).
_MIN_RATIO, _MAX_RATIO = 0.25, 4.0
# Les équivalences ci-dessus sont choisies à la main : on leur fait confiance
# même quand le facteur est grand (10 g de whey ≈ 100 g de fromage blanc).
_MIN_RATIO_EXPLICIT, _MAX_RATIO_EXPLICIT = 0.05, 20.0


@dataclass(frozen=True)
class Substitution:
    original: Food
    replacement: Food
    grams: float
    in_pantry: bool
    reason: str

    def describe(self) -> str:
        where = "déjà chez vous" if self.in_pantry else "à acheter"
        return (
            f"{self.original.name} → {self.replacement.name} "
            f"({self.grams:.0f} g, {where}) · {self.reason}"
        )


def _anchor_nutrient(food: Food) -> str:
    return _ANCHOR_BY_CATEGORY.get(food.category, "kcal")


def _converted_grams(
    original: Food, replacement: Food, grams: float, explicit: bool = False
) -> Optional[float]:
    """Quantité de remplacement calée sur le nutriment dominant.

    Renvoie None quand la conversion sort d'une plage raisonnable, ce qui
    revient à écarter le candidat.
    """
    anchor = _anchor_nutrient(original)
    src = getattr(original.per100g, anchor)
    dst = getattr(replacement.per100g, anchor)
    if src <= 0 or dst <= 0:
        src, dst = original.per100g.kcal, replacement.per100g.kcal
    if src <= 0 or dst <= 0:
        return None
    ratio = src / dst
    low, high = (
        (_MIN_RATIO_EXPLICIT, _MAX_RATIO_EXPLICIT) if explicit
        else (_MIN_RATIO, _MAX_RATIO)
    )
    if not (low <= ratio <= high):
        return None
    return max(5.0, round(grams * ratio / 5.0) * 5.0)


def _reason(original: Food, replacement: Food) -> str:
    anchor = _anchor_nutrient(original)
    labels = {
        "protein": "apport protéique équivalent",
        "carbs": "même rôle de source de glucides",
        "fat": "même apport en lipides",
        "kcal": "usage culinaire équivalent",
    }
    if original.category == replacement.category:
        return labels[anchor]
    return f"{labels[anchor]} (catégorie différente, à ajuster au goût)"


def _macro_profile(food: Food) -> tuple[float, float, float]:
    """Grammes de chaque macro pour 100 kcal — comparable entre aliments."""
    kcal = food.per100g.kcal or 1.0
    scale = 100.0 / kcal
    return (
        food.per100g.protein * scale,
        food.per100g.carbs * scale,
        food.per100g.fat * scale,
    )


def _profile_distance(a: Food, b: Food) -> float:
    pa, pb = _macro_profile(a), _macro_profile(b)
    return sum((x - y) ** 2 for x, y in zip(pa, pb)) ** 0.5


def _candidates(food_id: str) -> list[str]:
    """Candidats ordonnés : équivalences explicites puis même catégorie.

    Le repli « même catégorie » est trié par proximité du profil de macros pour
    éviter les remplacements cocasses (un oignon par du maïs, par exemple).
    """
    explicit = list(EQUIVALENCES.get(food_id, ()))
    food = FOODS.get(food_id)
    same_category = []
    if food:
        neighbours = [
            other
            for other in FOODS.values()
            if other.category == food.category and other.id != food_id
        ]
        neighbours.sort(key=lambda other: _profile_distance(food, other))
        same_category = [other.id for other in neighbours]
    seen, ordered = set(), []
    for candidate in explicit + same_category:
        if candidate not in seen:
            seen.add(candidate)
            ordered.append(candidate)
    return ordered


def suggest_substitute(
    food_id: str,
    grams: float,
    pantry: Optional[Mapping[str, float]] = None,
) -> Optional[Substitution]:
    """Meilleure substitution pour un ingrédient manquant.

    `pantry` associe un identifiant d'aliment à la quantité disponible (g).
    """
    original = FOODS.get(food_id)
    if original is None:
        return None
    pantry = pantry or {}

    explicit = set(EQUIVALENCES.get(food_id, ()))
    best_in_pantry: Optional[Substitution] = None
    best_to_buy: Optional[Substitution] = None

    for candidate_id in _candidates(food_id):
        replacement = FOODS.get(candidate_id)
        if replacement is None:
            continue
        converted = _converted_grams(
            original, replacement, grams, explicit=candidate_id in explicit
        )
        if converted is None:
            continue
        available = pantry.get(candidate_id, 0.0)
        substitution = Substitution(
            original=original,
            replacement=replacement,
            grams=converted,
            in_pantry=available >= converted,
            reason=_reason(original, replacement),
        )
        if substitution.in_pantry:
            if best_in_pantry is None:
                best_in_pantry = substitution
                # Un équivalent explicite disponible : inutile de chercher plus loin.
                if candidate_id in explicit:
                    return substitution
        elif best_to_buy is None and candidate_id in explicit:
            best_to_buy = substitution

    return best_in_pantry or best_to_buy


def substitutes_catalog(food_id: str, limit: int = 4) -> list[str]:
    """Noms des remplaçants habituels d'un aliment (affichage documentaire)."""
    explicit = set(EQUIVALENCES.get(food_id, ()))
    names = []
    for candidate_id in _candidates(food_id)[: limit * 2]:
        food = FOODS.get(candidate_id)
        if food and _converted_grams(
            get_food(food_id), food, 100, explicit=candidate_id in explicit
        ) is not None:
            names.append(food.name)
        if len(names) >= limit:
            break
    return names
