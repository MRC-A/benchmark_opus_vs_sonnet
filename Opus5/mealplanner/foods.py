"""Base d'aliments (valeurs pour 100 g de produit tel qu'il est stocké).

Les valeurs sont des ordres de grandeur issus des tables de composition usuelles
(type Ciqual / USDA). Les féculents sont exprimés **crus**, car c'est sous cette
forme qu'ils se trouvent dans un placard : le garde-manger et les recettes
parlent donc le même langage.

Colonnes : kcal, protéines, glucides, lipides, fibres (g) puis fer, calcium,
vitamine C, magnésium (mg) et oméga-3 ALA (g).
"""

from __future__ import annotations

from .models import Food, NutritionFacts

# Catégories utilisées par le moteur de substitution.
CATEGORIES = {
    "proteine_animale": "Protéines animales",
    "proteine_vegetale": "Protéines végétales",
    "feculent": "Féculents & céréales",
    "legume": "Légumes",
    "fruit": "Fruits",
    "laitier": "Produits laitiers",
    "matiere_grasse": "Matières grasses & oléagineux",
    "autre": "Autres",
}

# (id, nom, catégorie, kcal, P, G, L, fibres, fer, calcium, vit C, magnésium, oméga3,
#  poids unitaire, libellé unité)
_RAW: tuple[tuple, ...] = (
    # --- Protéines animales -------------------------------------------------
    ("poulet_blanc", "Blanc de poulet", "proteine_animale", 165, 31.0, 0.0, 3.6, 0.0, 0.7, 11, 0, 29, 0.03, 130, "un filet"),
    ("dinde_escalope", "Escalope de dinde", "proteine_animale", 135, 29.0, 0.0, 1.5, 0.0, 1.1, 12, 0, 28, 0.02, 110, "une escalope"),
    ("boeuf_hache_5", "Bœuf haché 5% MG", "proteine_animale", 137, 21.0, 0.0, 5.0, 0.0, 2.6, 11, 0, 22, 0.05, 125, "un steak"),
    ("saumon", "Saumon (filet)", "proteine_animale", 208, 20.0, 0.0, 13.0, 0.0, 0.34, 9, 0, 27, 2.50, 130, "un pavé"),
    ("thon_naturel", "Thon au naturel (boîte)", "proteine_animale", 116, 26.0, 0.0, 1.0, 0.0, 1.0, 10, 0, 30, 0.30, 112, "une boîte"),
    ("crevettes", "Crevettes décortiquées", "proteine_animale", 99, 24.0, 0.2, 0.3, 0.0, 0.5, 70, 0, 37, 0.50, None, None),
    ("oeuf", "Œuf entier", "proteine_animale", 143, 12.6, 0.7, 9.5, 0.0, 1.75, 56, 0, 12, 0.10, 60, "un œuf"),
    ("blanc_oeuf", "Blanc d'œuf", "proteine_animale", 52, 11.0, 0.7, 0.2, 0.0, 0.08, 7, 0, 11, 0.0, 33, "un blanc"),
    ("jambon_blanc", "Jambon blanc", "proteine_animale", 107, 20.0, 1.0, 2.5, 0.0, 0.8, 6, 0, 20, 0.02, 45, "une tranche"),
    # --- Protéines végétales ------------------------------------------------
    ("tofu_ferme", "Tofu ferme", "proteine_vegetale", 144, 15.0, 2.8, 8.0, 2.3, 2.7, 350, 0.1, 58, 0.60, None, None),
    ("lentilles", "Lentilles sèches", "proteine_vegetale", 352, 24.6, 63.0, 1.1, 10.7, 6.5, 35, 4.5, 47, 0.11, None, None),
    ("pois_chiches", "Pois chiches (boîte, égouttés)", "proteine_vegetale", 164, 8.9, 27.0, 2.6, 7.6, 2.9, 49, 1.3, 48, 0.10, 240, "une boîte"),
    ("haricots_rouges", "Haricots rouges (boîte)", "proteine_vegetale", 127, 8.7, 22.8, 0.5, 6.4, 2.9, 28, 1.2, 45, 0.10, 240, "une boîte"),
    ("whey", "Whey protéine (poudre)", "laitier", 380, 78.0, 6.0, 5.0, 1.0, 1.0, 400, 0, 60, 0.0, 30, "une dose"),
    # --- Féculents ----------------------------------------------------------
    ("riz_blanc", "Riz blanc (cru)", "feculent", 349, 7.1, 77.2, 0.7, 1.4, 0.8, 10, 0, 35, 0.01, None, None),
    ("riz_complet", "Riz complet (cru)", "feculent", 353, 7.9, 72.4, 2.8, 3.5, 1.5, 23, 0, 143, 0.03, None, None),
    ("pates", "Pâtes (crues)", "feculent", 359, 12.5, 71.0, 1.5, 3.2, 1.3, 21, 0, 53, 0.05, None, None),
    ("pates_completes", "Pâtes complètes (crues)", "feculent", 348, 13.5, 64.0, 2.5, 9.0, 3.6, 40, 0, 143, 0.06, None, None),
    ("quinoa", "Quinoa (cru)", "feculent", 368, 14.1, 64.2, 6.1, 7.0, 4.6, 47, 0, 197, 0.26, None, None),
    ("semoule", "Semoule / couscous (cru)", "feculent", 360, 12.7, 73.0, 1.1, 3.9, 1.2, 17, 0, 47, 0.02, None, None),
    ("flocons_avoine", "Flocons d'avoine", "feculent", 370, 13.0, 59.0, 7.0, 10.0, 4.0, 54, 0, 177, 0.10, None, None),
    ("pain_complet", "Pain complet", "feculent", 247, 9.7, 41.0, 3.4, 7.0, 2.5, 107, 0, 82, 0.05, 50, "une tranche"),
    ("tortilla_ble_complet", "Tortilla blé complet", "feculent", 290, 9.0, 46.0, 7.0, 6.0, 2.4, 80, 0, 60, 0.05, 60, "une tortilla"),
    ("patate_douce", "Patate douce (crue)", "feculent", 86, 1.6, 20.1, 0.1, 3.0, 0.6, 30, 2.4, 25, 0.01, 200, "une patate"),
    ("pomme_de_terre", "Pomme de terre (crue)", "feculent", 77, 2.0, 17.0, 0.1, 2.2, 0.8, 12, 19.7, 23, 0.01, 150, "une pomme de terre"),
    # --- Légumes ------------------------------------------------------------
    ("brocoli", "Brocoli", "legume", 34, 2.8, 4.0, 0.4, 3.3, 0.7, 47, 89.2, 21, 0.13, None, None),
    ("epinards", "Épinards", "legume", 23, 2.9, 1.4, 0.4, 2.2, 2.7, 99, 28.1, 79, 0.14, None, None),
    ("haricots_verts", "Haricots verts", "legume", 31, 1.8, 4.3, 0.2, 3.4, 1.0, 37, 12.2, 25, 0.06, None, None),
    ("courgette", "Courgette", "legume", 17, 1.2, 2.1, 0.3, 1.0, 0.4, 16, 17.9, 18, 0.05, 250, "une courgette"),
    ("poivron", "Poivron", "legume", 26, 1.0, 4.6, 0.3, 2.1, 0.4, 10, 128.0, 12, 0.02, 150, "un poivron"),
    ("tomate", "Tomate", "legume", 18, 0.9, 2.7, 0.2, 1.2, 0.3, 10, 14.0, 11, 0.003, 120, "une tomate"),
    ("oignon", "Oignon", "legume", 40, 1.1, 7.6, 0.1, 1.7, 0.2, 23, 7.4, 10, 0.004, 110, "un oignon"),
    ("carotte", "Carotte", "legume", 41, 0.9, 7.3, 0.2, 2.8, 0.3, 33, 5.9, 12, 0.002, 90, "une carotte"),
    ("champignons", "Champignons de Paris", "legume", 22, 3.1, 1.3, 0.3, 1.0, 0.5, 3, 2.1, 9, 0.0, None, None),
    ("salade_verte", "Salade verte", "legume", 15, 1.4, 1.5, 0.2, 1.3, 0.9, 36, 9.2, 13, 0.06, None, None),
    ("concombre", "Concombre", "legume", 15, 0.7, 3.6, 0.1, 0.5, 0.3, 16, 2.8, 13, 0.005, 300, "un concombre"),
    ("petits_pois", "Petits pois", "legume", 81, 5.4, 14.5, 0.4, 5.7, 1.5, 25, 40.0, 33, 0.04, None, None),
    ("mais_doux", "Maïs doux", "legume", 86, 3.3, 19.0, 1.2, 2.7, 0.5, 2, 6.8, 37, 0.02, None, None),
    ("sauce_tomate", "Sauce tomate", "legume", 32, 1.3, 7.0, 0.2, 1.5, 0.9, 14, 9.0, 13, 0.01, None, None),
    # --- Fruits -------------------------------------------------------------
    ("banane", "Banane", "fruit", 89, 1.1, 22.8, 0.3, 2.6, 0.26, 5, 8.7, 27, 0.03, 120, "une banane"),
    ("pomme", "Pomme", "fruit", 52, 0.3, 13.8, 0.2, 2.4, 0.12, 6, 4.6, 5, 0.01, 150, "une pomme"),
    ("orange", "Orange", "fruit", 47, 0.9, 11.8, 0.1, 2.4, 0.10, 40, 53.2, 10, 0.01, 180, "une orange"),
    ("myrtilles", "Myrtilles", "fruit", 57, 0.7, 14.5, 0.3, 2.4, 0.28, 6, 9.7, 6, 0.06, None, None),
    # --- Produits laitiers --------------------------------------------------
    ("fromage_blanc_0", "Fromage blanc 0%", "laitier", 47, 8.0, 4.0, 0.2, 0.0, 0.05, 120, 0.5, 11, 0.0, None, None),
    ("skyr", "Skyr nature", "laitier", 63, 11.0, 4.0, 0.2, 0.0, 0.05, 150, 0.5, 11, 0.0, 150, "un pot"),
    ("yaourt_grec", "Yaourt grec 2%", "laitier", 73, 9.0, 3.6, 2.0, 0.0, 0.04, 110, 0.5, 11, 0.01, 150, "un pot"),
    ("lait_demi_ecreme", "Lait demi-écrémé", "laitier", 46, 3.2, 4.8, 1.5, 0.0, 0.03, 120, 1.0, 11, 0.01, None, None),
    ("feta", "Feta", "laitier", 264, 14.0, 4.1, 21.0, 0.0, 0.65, 493, 0, 19, 0.20, None, None),
    ("mozzarella", "Mozzarella", "laitier", 254, 18.0, 2.2, 19.0, 0.0, 0.40, 505, 0, 20, 0.10, 125, "une boule"),
    ("parmesan", "Parmesan râpé", "laitier", 402, 36.0, 3.2, 27.0, 0.0, 0.80, 1180, 0, 44, 0.20, None, None),
    # --- Matières grasses & oléagineux --------------------------------------
    ("huile_olive", "Huile d'olive", "matiere_grasse", 884, 0.0, 0.0, 100.0, 0.0, 0.56, 1, 0, 0, 0.76, 10, "une c. à soupe"),
    ("huile_colza", "Huile de colza", "matiere_grasse", 884, 0.0, 0.0, 100.0, 0.0, 0.0, 0, 0, 0, 9.10, 10, "une c. à soupe"),
    ("beurre_cacahuete", "Beurre de cacahuète", "matiere_grasse", 588, 25.0, 20.0, 50.0, 6.0, 1.9, 43, 0, 168, 0.05, 16, "une c. à soupe"),
    ("amandes", "Amandes", "matiere_grasse", 579, 21.0, 21.6, 49.9, 12.5, 3.7, 269, 0, 270, 0.003, None, None),
    ("noix", "Noix (cerneaux)", "matiere_grasse", 654, 15.0, 13.7, 65.0, 6.7, 2.9, 98, 1.3, 158, 9.10, None, None),
    ("graines_chia", "Graines de chia", "matiere_grasse", 486, 17.0, 42.0, 31.0, 34.0, 7.7, 631, 1.6, 335, 17.80, None, None),
    ("avocat", "Avocat", "matiere_grasse", 160, 2.0, 8.5, 14.7, 6.7, 0.55, 12, 10.0, 29, 0.11, 170, "un avocat"),
    # --- Autres -------------------------------------------------------------
    ("miel", "Miel", "autre", 304, 0.3, 82.0, 0.0, 0.2, 0.4, 6, 0.5, 2, 0.0, 20, "une c. à soupe"),
    ("chocolat_noir_70", "Chocolat noir 70%", "autre", 546, 7.8, 45.9, 31.3, 11.0, 11.9, 73, 0, 228, 0.03, 10, "un carré"),
)


def _build() -> dict[str, Food]:
    catalog: dict[str, Food] = {}
    for row in _RAW:
        (fid, name, cat, kcal, prot, carbs, fat, fiber, iron, calcium,
         vit_c, magnesium, omega3, unit_g, unit_label) = row
        catalog[fid] = Food(
            id=fid,
            name=name,
            category=cat,
            per100g=NutritionFacts(
                kcal=float(kcal), protein=float(prot), carbs=float(carbs),
                fat=float(fat), fiber=float(fiber), iron=float(iron),
                calcium=float(calcium), vitamin_c=float(vit_c),
                magnesium=float(magnesium), omega3=float(omega3),
            ),
            unit_grams=float(unit_g) if unit_g else None,
            unit_label=unit_label,
        )
    return catalog


FOODS: dict[str, Food] = _build()


def get_food(food_id: str) -> Food:
    try:
        return FOODS[food_id]
    except KeyError as exc:  # pragma: no cover - garde-fou de développement
        raise KeyError(f"Aliment inconnu : {food_id!r}") from exc


def food_name(food_id: str) -> str:
    food = FOODS.get(food_id)
    return food.name if food else food_id


def foods_by_category() -> dict[str, list[Food]]:
    grouped: dict[str, list[Food]] = {key: [] for key in CATEGORIES}
    for food in FOODS.values():
        grouped.setdefault(food.category, []).append(food)
    for items in grouped.values():
        items.sort(key=lambda f: f.name)
    return grouped


def richest_in(nutrient: str, limit: int = 5, exclude: tuple[str, ...] = ()) -> list[Food]:
    """Aliments les plus denses en un nutriment, rapportés à 100 kcal.

    Rapporter à l'énergie évite de ne proposer que des aliments très caloriques
    (l'huile de colza pour les oméga-3, par exemple).
    """
    scored = []
    for food in FOODS.values():
        if food.id in exclude or food.per100g.kcal <= 0:
            continue
        density = getattr(food.per100g, nutrient) / food.per100g.kcal * 100.0
        if density > 0:
            scored.append((density, food))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [food for _, food in scored[:limit]]
