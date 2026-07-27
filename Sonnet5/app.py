"""Point d'entrée de l'application Streamlit.

Ce fichier ne contient QUE de l'interface : toute la logique métier
(calcul de macros, suggestions, suivi) vit dans le package `meal_planner`.
Lancer avec : streamlit run app.py
"""

from datetime import date, timedelta

import streamlit as st

from meal_planner import storage, suggestions, tracking
from meal_planner.macros import calculate_daily_macros, distribute_macros_by_meal
from meal_planner.models import (
    ACTIVITY_LEVELS, GOALS, MEAL_LABELS, MEAL_TYPES, SEXES, MealLogEntry, UserProfile,
)
from meal_planner.recipes_data import RECIPES

st.set_page_config(page_title="Planificateur de repas", page_icon="🍽️", layout="wide")
storage.init_db()


def get_meal_target(profile, meal_type):
    daily = calculate_daily_macros(profile)
    return distribute_macros_by_meal(daily)[meal_type]


# ----------------------------------------------------------------- Sidebar --

st.sidebar.title("🍽️ Planificateur de repas")
page = st.sidebar.radio(
    "Navigation",
    ["Profil", "Mes aliments", "Suggestions de repas", "Recettes de base", "Journal & Suivi"],
)

profile = storage.get_profile()

if profile is None and page != "Profil":
    st.warning("Renseigne d'abord ton profil dans l'onglet **Profil** pour débloquer les autres fonctionnalités.")
    st.stop()


# ------------------------------------------------------------------- Profil --

if page == "Profil":
    st.header("Ton profil")
    st.caption("Ces informations servent uniquement à calculer tes besoins caloriques et tes macros cibles.")

    with st.form("profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            weight = st.number_input("Poids (kg)", min_value=30.0, max_value=250.0,
                                      value=profile.weight_kg if profile else 70.0, step=0.5)
            height = st.number_input("Taille (cm)", min_value=120.0, max_value=230.0,
                                      value=profile.height_cm if profile else 175.0, step=1.0)
            age = st.number_input("Âge", min_value=14, max_value=100,
                                   value=profile.age if profile else 30, step=1)
        with col2:
            sex = st.selectbox("Sexe", SEXES, index=SEXES.index(profile.sex) if profile else 0)
            activity = st.selectbox("Niveau d'activité sportive", ACTIVITY_LEVELS,
                                     index=ACTIVITY_LEVELS.index(profile.activity_level) if profile else 0)
            goal = st.selectbox("Objectif", GOALS, index=GOALS.index(profile.goal) if profile else 0)

        submitted = st.form_submit_button("Enregistrer mon profil")

    if submitted:
        new_profile = UserProfile(weight_kg=weight, height_cm=height, age=int(age),
                                   sex=sex, activity_level=activity, goal=goal)
        storage.save_profile(new_profile)
        st.success("Profil enregistré !")
        profile = new_profile

    if profile:
        st.subheader("Tes besoins quotidiens estimés")
        daily = calculate_daily_macros(profile)
        cols = st.columns(4)
        cols[0].metric("Calories", f"{daily['calories']} kcal")
        cols[1].metric("Protéines", f"{daily['protein_g']} g")
        cols[2].metric("Glucides", f"{daily['carbs_g']} g")
        cols[3].metric("Lipides", f"{daily['fat_g']} g")

        st.subheader("Répartition par repas")
        per_meal = distribute_macros_by_meal(daily)
        rows = []
        for meal_type in MEAL_TYPES:
            m = per_meal[meal_type]
            rows.append({
                "Repas": MEAL_LABELS[meal_type],
                "Calories": m["calories"],
                "Protéines (g)": m["protein_g"],
                "Glucides (g)": m["carbs_g"],
                "Lipides (g)": m["fat_g"],
            })
        st.table(rows)


# -------------------------------------------------------------- Mes aliments --

elif page == "Mes aliments":
    st.header("Mes aliments disponibles")

    col1, col2, col3 = st.columns([2, 1, 1])
    name = col1.text_input("Nom de l'aliment (ex: poulet, riz, oeufs...)", key="new_food_name")
    quantity = col2.number_input("Quantité (g)", min_value=0.0, value=200.0, step=10.0, key="new_food_qty")
    has_expiration = col3.checkbox("Date de péremption connue ?", key="new_food_has_exp")
    expiration = None
    if has_expiration:
        expiration = st.date_input("Péremption approximative", value=date.today() + timedelta(days=5),
                                    key="new_food_exp")

    if st.button("Ajouter à mon inventaire") and name.strip():
        storage.add_food(name, quantity, expiration)
        st.success(f"{name} ajouté.")
        st.rerun()

    foods = storage.get_foods()
    if not foods:
        st.info("Aucun aliment enregistré pour l'instant.")
    else:
        st.subheader("Inventaire actuel")
        today = date.today()
        for food in foods:
            cols = st.columns([2, 1, 1, 1])
            cols[0].write(f"**{food.name.capitalize()}**")
            cols[1].write(f"{food.quantity_g:g} g")
            if food.expiration_date:
                days_left = (food.expiration_date - today).days
                if days_left < 0:
                    cols[2].write("⚠️ Périmé")
                elif days_left <= 3:
                    cols[2].write(f"🔴 dans {days_left} j")
                elif days_left <= 7:
                    cols[2].write(f"🟠 dans {days_left} j")
                else:
                    cols[2].write(f"🟢 dans {days_left} j")
            else:
                cols[2].write("—")
            if cols[3].button("Supprimer", key=f"del_{food.id}"):
                storage.delete_food(food.id)
                st.rerun()


# ------------------------------------------------------- Suggestions de repas --

elif page == "Suggestions de repas":
    st.header("Que puis-je manger avec ce que j'ai ?")

    col1, col2 = st.columns(2)
    selected_date = col1.date_input("Date du repas", value=date.today())
    meal_type = col2.selectbox("Repas", MEAL_TYPES, format_func=lambda m: MEAL_LABELS[m])

    target = get_meal_target(profile, meal_type)
    st.caption(
        f"Objectif pour ce repas : ~{target['calories']} kcal · "
        f"{target['protein_g']} g protéines · {target['carbs_g']} g glucides · {target['fat_g']} g lipides"
    )

    inventory = storage.get_foods()
    if not inventory:
        st.info("Ajoute des aliments dans l'onglet **Mes aliments** pour obtenir des suggestions.")
    else:
        results = suggestions.suggest_recipes_for_meal(RECIPES, inventory, meal_type, target, today=selected_date)
        if not results:
            st.info("Aucune recette de la base ne correspond à ce type de repas.")
        for i, result in enumerate(results):
            recipe = result["recipe"]
            with st.container(border=True):
                title = f"### {recipe.name}"
                if result["can_make_fully"]:
                    title += " ✅"
                if result["uses_expiring_soon"]:
                    title += " ⏳ utilise des aliments à péremption proche"
                st.markdown(title)
                st.write(
                    f"{recipe.calories} kcal · {recipe.protein_g} g protéines · "
                    f"{recipe.carbs_g} g glucides · {recipe.fat_g} g lipides · {recipe.fiber_g} g fibres"
                )
                if result["missing_ingredients"]:
                    st.markdown("**Ingrédients manquants :**")
                    for missing in result["missing_ingredients"]:
                        subs = missing["substitutes"]
                        sub_text = f" — remplaçable par : {', '.join(subs)}" if subs else ""
                        st.write(f"- {missing['ingredient']}{sub_text}")
                if st.button("Logger ce repas", key=f"log_{i}"):
                    entry = MealLogEntry(
                        log_date=selected_date, meal_type=meal_type, recipe_name=recipe.name,
                        calories=recipe.calories, protein_g=recipe.protein_g,
                        carbs_g=recipe.carbs_g, fat_g=recipe.fat_g, fiber_g=recipe.fiber_g,
                    )
                    storage.log_meal(entry)
                    for ingredient_name, needed_qty in recipe.ingredients.items():
                        food = suggestions.find_matching_food(ingredient_name, inventory)
                        if food is not None and food.quantity_g >= needed_qty:
                            storage.update_food_quantity(food.id, food.quantity_g - needed_qty)
                    st.success("Repas ajouté à ton journal !")
                    st.rerun()


# ------------------------------------------------------------- Recettes de base --

elif page == "Recettes de base":
    st.header("Recettes de base (nutrition sportive)")
    rows = [{
        "Recette": r.name,
        "Repas": ", ".join(MEAL_LABELS[m] for m in r.meal_types),
        "Calories": r.calories,
        "Protéines (g)": r.protein_g,
        "Glucides (g)": r.carbs_g,
        "Lipides (g)": r.fat_g,
        "Fibres (g)": r.fiber_g,
    } for r in RECIPES]
    st.dataframe(rows, use_container_width=True, hide_index=True)


# ----------------------------------------------------------------- Journal --

elif page == "Journal & Suivi":
    st.header("Journal & suivi nutritionnel")

    st.subheader("Analyse des 7 derniers jours")
    alerts = tracking.analyze_deficiencies(profile)
    if alerts:
        for alert in alerts:
            st.warning(alert)
    else:
        st.success("Aucun déséquilibre récurrent détecté sur les derniers jours suivis.")

    st.subheader("Historique des repas loggés")
    logs = storage.get_logs()
    if not logs:
        st.info("Aucun repas loggé pour l'instant. Log tes repas depuis l'onglet **Suggestions de repas**.")
    else:
        rows = [{
            "Date": entry.log_date.isoformat(),
            "Repas": MEAL_LABELS[entry.meal_type],
            "Plat": entry.recipe_name,
            "Calories": entry.calories,
            "Protéines (g)": entry.protein_g,
            "Glucides (g)": entry.carbs_g,
            "Lipides (g)": entry.fat_g,
            "Fibres (g)": entry.fiber_g,
        } for entry in logs]
        st.dataframe(rows, use_container_width=True, hide_index=True)
