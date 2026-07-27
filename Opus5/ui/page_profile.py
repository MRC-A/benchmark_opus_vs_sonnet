"""Page « Profil » : saisie des données personnelles et objectifs qui en découlent."""

from __future__ import annotations

import streamlit as st

from mealplanner import nutrition
from mealplanner.models import Profile

from .shared import get_store, load_profile, macro_line


def render() -> None:
    st.header("Votre profil")
    st.caption(
        "Ces quelques informations suffisent : l'application en déduit seule "
        "vos besoins et leur répartition sur la journée."
    )

    profile = load_profile() or Profile()
    activity_keys = list(nutrition.ACTIVITY_LEVELS)

    with st.form("profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            sex = st.radio(
                "Sexe", ["homme", "femme"],
                index=0 if profile.sex == "homme" else 1,
                horizontal=True,
            )
            age = st.number_input("Âge", 14, 100, int(profile.age), step=1)
            weight = st.number_input(
                "Poids (kg)", 35.0, 200.0, float(profile.weight_kg), step=0.5
            )
            height = st.number_input(
                "Taille (cm)", 130.0, 220.0, float(profile.height_cm), step=1.0
            )
        with col2:
            activity = st.selectbox(
                "Niveau d'activité sportive",
                activity_keys,
                index=activity_keys.index(profile.activity)
                if profile.activity in activity_keys else 2,
                format_func=lambda key: nutrition.ACTIVITY_LEVELS[key].label,
            )
            st.caption(nutrition.ACTIVITY_LEVELS[activity].hint)

            available_goals = nutrition.goals_for(activity)
            goal_keys = list(available_goals)
            goal_index = goal_keys.index(profile.goal) if profile.goal in goal_keys else 0
            goal = st.selectbox(
                "Objectif",
                goal_keys,
                index=goal_index,
                format_func=lambda key: nutrition.GOALS[key].label,
            )
            st.caption(nutrition.GOALS[goal].hint)

            meals = st.select_slider(
                "Nombre de repas par jour", options=[3, 4, 5],
                value=profile.meals_per_day if profile.meals_per_day in (3, 4, 5) else 4,
            )

        if not nutrition.is_athlete(activity):
            st.caption(
                "ℹ️ Les objectifs de prise de masse et de sèche apparaissent à partir "
                "de 3 séances de sport par semaine : ils supposent un entraînement "
                "régulier pour être pertinents."
            )

        submitted = st.form_submit_button("Enregistrer mon profil", type="primary")

    if submitted:
        # Le sélecteur d'objectif est reconstruit à chaque rerender ; on garde
        # tout de même un garde-fou si l'activité vient de changer.
        if goal not in nutrition.goals_for(activity):
            goal = nutrition.default_goal(activity)
        new_profile = Profile(
            weight_kg=float(weight), height_cm=float(height), age=int(age),
            sex=sex, activity=activity, goal=goal, meals_per_day=int(meals),
        )
        get_store().save_profile(new_profile)
        st.success("Profil enregistré. Vos objectifs ont été recalculés.")
        profile = new_profile

    _render_summary(profile)


def _render_summary(profile: Profile) -> None:
    targets = nutrition.daily_targets(profile)

    st.divider()
    st.subheader("Vos besoins journaliers")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Calories", f"{targets.kcal:.0f} kcal")
    col2.metric("Protéines", f"{targets.protein:.0f} g",
                f"{nutrition.GOALS[profile.goal].protein_g_kg:g} g/kg")
    col3.metric("Glucides", f"{targets.carbs:.0f} g")
    col4.metric("Lipides", f"{targets.fat:.0f} g")

    split = nutrition.macro_energy_split(targets)
    st.caption(
        f"Répartition énergétique : protéines {split['protein']:.0f} % · "
        f"glucides {split['carbs']:.0f} % · lipides {split['fat']:.0f} %  |  "
        f"Métabolisme de base {targets.bmr:.0f} kcal, dépense estimée "
        f"{targets.tdee:.0f} kcal"
    )

    with st.expander("Comment ces chiffres sont obtenus"):
        goal = nutrition.GOALS[profile.goal]
        delta_pct = goal.kcal_delta * 100
        st.markdown(
            f"""
1. **Métabolisme de base** (Mifflin-St Jeor) : **{targets.bmr:.0f} kcal**.
2. **Dépense totale** × facteur d'activité
   ({nutrition.ACTIVITY_LEVELS[profile.activity].factor}) : **{targets.tdee:.0f} kcal**.
3. **Objectif « {goal.label} »** : {delta_pct:+.0f} % → **{targets.kcal:.0f} kcal**.
4. **Protéines** ancrées sur le poids de corps ({goal.protein_g_kg:g} g/kg), pas sur
   un pourcentage : c'est ce qui différencie réellement un profil sportif d'un
   profil sédentaire.
5. **Lipides** = {goal.fat_ratio * 100:.0f} % de l'énergie, avec un plancher de
   0,8 g/kg pour préserver l'équilibre hormonal.
6. **Glucides** = le reste de l'énergie disponible.
            """
        )

    st.subheader("Répartition sur la journée")
    meal_targets = nutrition.split_by_meal(targets, profile.meals_per_day)
    columns = st.columns(len(meal_targets))
    for column, meal in zip(columns, meal_targets):
        with column:
            st.markdown(f"**{meal.label}**")
            st.markdown(macro_line(meal.as_facts()))
            st.caption(f"{meal.kcal / targets.kcal * 100:.0f} % de la journée")

    st.caption(
        "Les glucides sont concentrés le matin et autour de l'entraînement, les "
        "lipides décalés vers le soir, les protéines réparties régulièrement."
    )

    with st.expander("Repères en micronutriments suivis"):
        st.markdown(
            f"""
| Nutriment | Objectif / jour |
| --- | --- |
| Fibres | {targets.fiber:.0f} g |
| Fer | {targets.iron:.0f} mg |
| Calcium | {targets.calcium:.0f} mg |
| Vitamine C | {targets.vitamin_c:.0f} mg |
| Magnésium | {targets.magnesium:.0f} mg |
| Oméga-3 (ALA) | {targets.omega3:.1f} g |
            """
        )
        st.caption(
            "Ces repères ne sont pas affichés au quotidien : ils servent à la "
            "détection de carences sur 7 jours glissants."
        )
