"""Recettes de base du répertoire « nutrition sportive ».

Les macros ne sont **jamais** codées en dur : elles sont recalculées depuis la
base d'aliments. Une correction dans `foods.py` se propage donc partout, et une
recette ne peut pas diverger de ses ingrédients.

Les quantités sont données pour une portion de référence, avec les féculents
exprimés crus (cohérent avec le garde-manger).
"""

from __future__ import annotations

from .foods import get_food
from .models import NutritionFacts, Recipe, RecipeIngredient

# Repas auxquels une recette peut être proposée.
MEAL_PETIT_DEJ = "petit_dej"
MEAL_DEJEUNER = "dejeuner"
MEAL_DINER = "diner"
MEAL_COLLATION = "collation"
MEAL_COLLATION_MATIN = "collation_matin"


def _ing(food_id: str, grams: float, optional: bool = False) -> RecipeIngredient:
    get_food(food_id)  # échoue tôt si l'identifiant est erroné
    return RecipeIngredient(food_id=food_id, grams=float(grams), optional=optional)


RECIPES: tuple[Recipe, ...] = (
    Recipe(
        id="riz_poulet_brocolis",
        name="Riz, poulet & brocolis",
        meals=(MEAL_DEJEUNER, MEAL_DINER),
        ingredients=(
            _ing("poulet_blanc", 150),
            _ing("riz_blanc", 80),
            _ing("brocoli", 200),
            _ing("oignon", 40, optional=True),
            _ing("huile_olive", 10),
        ),
        steps=(
            "Faire cuire le riz 12 minutes dans deux fois son volume d'eau salée.",
            "Saisir le poulet coupé en cubes dans l'huile avec l'oignon émincé.",
            "Cuire le brocoli 6 minutes à la vapeur, puis tout assembler.",
        ),
        prep_minutes=25,
        tags=("classique", "sans lactose"),
    ),
    Recipe(
        id="oeufs_avoine",
        name="Œufs brouillés & porridge d'avoine",
        meals=(MEAL_PETIT_DEJ,),
        ingredients=(
            _ing("oeuf", 120),
            _ing("flocons_avoine", 60),
            _ing("lait_demi_ecreme", 150),
            _ing("banane", 100),
            _ing("miel", 10, optional=True),
        ),
        steps=(
            "Chauffer les flocons d'avoine dans le lait 4 minutes en remuant.",
            "Brouiller les œufs à feu doux dans une poêle antiadhésive.",
            "Servir le porridge garni de banane et de miel, les œufs à côté.",
        ),
        prep_minutes=12,
        tags=("petit-déjeuner", "rapide"),
    ),
    Recipe(
        id="saumon_patate_epinards",
        name="Saumon, patate douce & épinards",
        meals=(MEAL_DEJEUNER, MEAL_DINER),
        ingredients=(
            _ing("saumon", 150),
            _ing("patate_douce", 250),
            _ing("epinards", 150),
            _ing("huile_olive", 8),
        ),
        steps=(
            "Rôtir la patate douce en cubes 25 minutes à 200 °C avec l'huile.",
            "Cuire le saumon 10 minutes à la poêle, côté peau d'abord.",
            "Faire tomber les épinards 3 minutes et servir.",
        ),
        prep_minutes=30,
        tags=("oméga-3", "sans lactose"),
    ),
    Recipe(
        id="boeuf_pates_courgettes",
        name="Pâtes complètes bolognaise de bœuf",
        meals=(MEAL_DEJEUNER, MEAL_DINER),
        ingredients=(
            _ing("boeuf_hache_5", 150),
            _ing("pates_completes", 90),
            _ing("courgette", 150),
            _ing("sauce_tomate", 120),
            _ing("oignon", 50, optional=True),
            _ing("huile_olive", 8),
        ),
        steps=(
            "Faire revenir l'oignon et la courgette en dés dans l'huile.",
            "Ajouter le bœuf haché, puis la sauce tomate ; mijoter 10 minutes.",
            "Cuire les pâtes al dente et mélanger.",
        ),
        prep_minutes=25,
        tags=("riche en fer",),
    ),
    Recipe(
        id="bowl_skyr_banane",
        name="Bowl skyr, banane & beurre de cacahuète",
        meals=(MEAL_COLLATION, MEAL_COLLATION_MATIN, MEAL_PETIT_DEJ),
        ingredients=(
            _ing("skyr", 200),
            _ing("banane", 100),
            _ing("flocons_avoine", 40),
            _ing("beurre_cacahuete", 20),
            _ing("myrtilles", 60, optional=True),
        ),
        steps=(
            "Verser le skyr dans un bol, ajouter les flocons d'avoine.",
            "Garnir de banane en rondelles, de myrtilles et de beurre de cacahuète.",
        ),
        prep_minutes=5,
        tags=("sans cuisson", "collation"),
    ),
    Recipe(
        id="thon_quinoa_haricots",
        name="Quinoa, thon & haricots verts",
        meals=(MEAL_DEJEUNER, MEAL_DINER),
        ingredients=(
            _ing("thon_naturel", 120),
            _ing("quinoa", 70),
            _ing("haricots_verts", 200),
            _ing("tomate", 100, optional=True),
            _ing("huile_olive", 10),
        ),
        steps=(
            "Rincer puis cuire le quinoa 15 minutes dans de l'eau salée.",
            "Cuire les haricots verts 8 minutes à la vapeur.",
            "Mélanger avec le thon émietté, la tomate en dés et l'huile.",
        ),
        prep_minutes=20,
        tags=("rapide", "sans lactose"),
    ),
    Recipe(
        id="omelette_pdt_poivrons",
        name="Omelette blancs d'œufs, pommes de terre & poivrons",
        meals=(MEAL_PETIT_DEJ, MEAL_DEJEUNER, MEAL_DINER),
        ingredients=(
            _ing("blanc_oeuf", 200),
            _ing("oeuf", 60),
            _ing("pomme_de_terre", 250),
            _ing("poivron", 120),
            _ing("huile_olive", 8),
        ),
        steps=(
            "Faire sauter les pommes de terre en cubes et le poivron 15 minutes.",
            "Verser les blancs battus avec l'œuf entier, cuire à couvert 5 minutes.",
        ),
        prep_minutes=22,
        tags=("très protéiné", "peu de lipides"),
    ),
    Recipe(
        id="wrap_dinde_avocat",
        name="Wrap dinde & avocat",
        meals=(MEAL_DEJEUNER, MEAL_COLLATION),
        ingredients=(
            _ing("tortilla_ble_complet", 60),
            _ing("dinde_escalope", 120),
            _ing("avocat", 60),
            _ing("fromage_blanc_0", 40),
            _ing("tomate", 60, optional=True),
            _ing("salade_verte", 40, optional=True),
        ),
        steps=(
            "Poêler l'escalope de dinde et la découper en lanières.",
            "Tartiner la tortilla de fromage blanc, garnir et rouler serré.",
        ),
        prep_minutes=12,
        tags=("nomade", "rapide"),
    ),
    Recipe(
        id="dhal_lentilles_riz",
        name="Dhal de lentilles & riz basmati",
        meals=(MEAL_DEJEUNER, MEAL_DINER),
        ingredients=(
            _ing("lentilles", 90),
            _ing("riz_blanc", 60),
            _ing("epinards", 80),
            _ing("carotte", 80),
            _ing("oignon", 60, optional=True),
            _ing("sauce_tomate", 100),
            _ing("huile_colza", 10),
        ),
        steps=(
            "Faire suer l'oignon et la carotte, ajouter les épices.",
            "Ajouter lentilles, sauce tomate et 400 ml d'eau ; mijoter 25 minutes.",
            "Incorporer les épinards en fin de cuisson, servir avec le riz.",
        ),
        prep_minutes=35,
        tags=("végétarien", "riche en fibres"),
    ),
    Recipe(
        id="pancakes_proteines",
        name="Pancakes protéinés avoine & banane",
        meals=(MEAL_PETIT_DEJ, MEAL_COLLATION),
        ingredients=(
            _ing("flocons_avoine", 60),
            _ing("blanc_oeuf", 150),
            _ing("banane", 100),
            _ing("whey", 20, optional=True),
            _ing("fromage_blanc_0", 60, optional=True),
        ),
        steps=(
            "Mixer flocons, blancs d'œufs, banane et whey en pâte lisse.",
            "Cuire de petites louches 2 minutes par face à feu moyen.",
            "Servir avec le fromage blanc.",
        ),
        prep_minutes=15,
        tags=("petit-déjeuner", "sucré"),
    ),
)

RECIPES_BY_ID: dict[str, Recipe] = {recipe.id: recipe for recipe in RECIPES}


def recipe_facts(recipe: Recipe, portions: float = 1.0) -> NutritionFacts:
    """Valeurs nutritionnelles d'une recette pour un nombre de portions donné."""
    total = NutritionFacts.sum(
        get_food(ing.food_id).facts_for(ing.grams) for ing in recipe.ingredients
    )
    return total * portions


def recipes_for_meal(meal_key: str) -> list[Recipe]:
    """Recettes adaptées à un repas, avec repli sur tout le catalogue."""
    matching = [r for r in RECIPES if meal_key in r.meals]
    return matching or list(RECIPES)


def recipe_name(recipe_id: str | None) -> str:
    if not recipe_id:
        return "Repas libre"
    recipe = RECIPES_BY_ID.get(recipe_id)
    return recipe.name if recipe else recipe_id
