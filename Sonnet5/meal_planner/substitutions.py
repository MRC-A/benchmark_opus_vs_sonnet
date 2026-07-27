"""Substitutions basiques d'ingrédients.

Pas de recalcul de macros à l'identique : on propose simplement une
alternative raisonnable, proche en usage culinaire et en profil
nutritionnel général.
"""

SUBSTITUTIONS = {
    "poulet": ["dinde", "tofu", "poisson blanc"],
    "dinde": ["poulet", "tofu"],
    "boeuf haché": ["dinde hachée", "poulet haché"],
    "saumon": ["thon", "maquereau", "poulet"],
    "thon": ["saumon", "poulet"],
    "riz": ["quinoa", "pâtes", "boulgour"],
    "pâtes": ["riz", "quinoa"],
    "quinoa": ["riz", "boulgour"],
    "patate douce": ["pomme de terre", "riz"],
    "avoine": ["flocons de sarrasin", "muesli sans sucre"],
    "oeufs": ["blancs d'oeufs", "tofu soyeux"],
    "brocolis": ["haricots verts", "épinards", "courgettes"],
    "épinards": ["mâche", "roquette", "brocolis"],
    "tomates": ["poivrons", "courgettes"],
    "poivrons": ["tomates", "courgettes"],
    "légumes": ["légumes surgelés mélangés"],
    "skyr": ["fromage blanc 0%", "yaourt grec"],
    "yaourt grec": ["skyr", "fromage blanc"],
    "fromage": ["fromage blanc", "mozzarella light"],
    "lait": ["lait d'amande", "lait de soja"],
    "banane": ["compote de pommes sans sucre", "poire"],
    "miel": ["sirop d'agave", "confiture allégée"],
    "pain complet": ["pain de seigle", "galette de riz"],
    "wrap": ["pain pita", "tortilla de maïs"],
    "avocat": ["houmous", "purée d'amande"],
    "granola": ["flocons d'avoine grillés", "muesli"],
    "fruits rouges": ["pomme", "banane"],
    "pois chiches": ["lentilles", "haricots rouges"],
    "huile d'olive": ["huile de colza", "huile de tournesol"],
}


def suggest_substitute(ingredient_name: str):
    """Retourne une liste de substituts possibles (peut être vide)."""
    return SUBSTITUTIONS.get(ingredient_name.strip().lower(), [])
