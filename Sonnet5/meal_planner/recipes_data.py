"""Base de recettes classiques de nutrition sportive / musculation.

Les quantités d'ingrédients sont en grammes (ou unités pour les oeufs,
comptées comme ~55g). Les macros sont données pour une portion complète
de la recette telle que décrite par ses ingrédients.
"""

from .models import Recipe

RECIPES = [
    Recipe(
        name="Riz - Poulet - Brocolis",
        meal_types=["dejeuner", "diner"],
        ingredients={"riz": 150, "poulet": 150, "brocolis": 200, "huile d'olive": 10},
        calories=560, protein_g=48, carbs_g=68, fat_g=12, fiber_g=6,
    ),
    Recipe(
        name="Oeufs - Avoine (porridge protéiné)",
        meal_types=["petit_dejeuner"],
        ingredients={"avoine": 80, "oeufs": 110, "lait": 200, "miel": 15},
        calories=520, protein_g=28, carbs_g=62, fat_g=16, fiber_g=7,
    ),
    Recipe(
        name="Pâtes - Thon - Tomates",
        meal_types=["dejeuner", "diner"],
        ingredients={"pâtes": 150, "thon": 120, "tomates": 150, "huile d'olive": 10},
        calories=580, protein_g=42, carbs_g=78, fat_g=12, fiber_g=5,
    ),
    Recipe(
        name="Patate douce - Saumon - Épinards",
        meal_types=["dejeuner", "diner"],
        ingredients={"patate douce": 200, "saumon": 150, "épinards": 150, "huile d'olive": 10},
        calories=560, protein_g=38, carbs_g=48, fat_g=22, fiber_g=7,
    ),
    Recipe(
        name="Skyr - Flocons d'avoine - Banane - Miel",
        meal_types=["petit_dejeuner", "collation"],
        ingredients={"skyr": 200, "avoine": 50, "banane": 100, "miel": 10},
        calories=430, protein_g=32, carbs_g=62, fat_g=4, fiber_g=5,
    ),
    Recipe(
        name="Omelette - Fromage - Pain complet",
        meal_types=["petit_dejeuner", "diner"],
        ingredients={"oeufs": 165, "fromage": 40, "pain complet": 80},
        calories=520, protein_g=34, carbs_g=38, fat_g=26, fiber_g=5,
    ),
    Recipe(
        name="Riz - Boeuf haché - Poivrons",
        meal_types=["dejeuner", "diner"],
        ingredients={"riz": 150, "boeuf haché": 150, "poivrons": 150, "huile d'olive": 10},
        calories=610, protein_g=42, carbs_g=68, fat_g=18, fiber_g=5,
    ),
    Recipe(
        name="Wrap - Dinde - Avocat",
        meal_types=["dejeuner", "collation"],
        ingredients={"wrap": 80, "dinde": 120, "avocat": 80, "légumes": 50},
        calories=480, protein_g=34, carbs_g=38, fat_g=20, fiber_g=6,
    ),
    Recipe(
        name="Yaourt grec - Granola - Fruits rouges",
        meal_types=["petit_dejeuner", "collation"],
        ingredients={"yaourt grec": 200, "granola": 50, "fruits rouges": 100},
        calories=390, protein_g=22, carbs_g=48, fat_g=12, fiber_g=6,
    ),
    Recipe(
        name="Quinoa - Pois chiches - Légumes",
        meal_types=["dejeuner", "diner"],
        ingredients={"quinoa": 150, "pois chiches": 150, "légumes": 200, "huile d'olive": 10},
        calories=540, protein_g=26, carbs_g=78, fat_g=14, fiber_g=14,
    ),
]
