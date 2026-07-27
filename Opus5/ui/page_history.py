"""Page « Suivi » : historique des repas et détection de déséquilibres."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from mealplanner.analytics import trend_table
from mealplanner.models import MealLog, NutritionFacts
from mealplanner.nutrition import MEAL_LABELS
from mealplanner.recipes import RECIPES, recipe_facts

from .shared import (
    get_store,
    meal_targets_for,
    refresh,
    render_alerts,
    require_profile,
    targets_for,
    week_report,
)


def render() -> None:
    profile = require_profile()
    store = get_store()
    today = date.today()
    targets = targets_for(profile)

    st.header("Suivi")

    window = st.segmented_control(
        "Fenêtre d'analyse", options=[7, 14, 30],
        format_func=lambda days: f"{days} jours", default=7,
    ) or 7

    report = week_report(profile, today, window_days=window)

    st.subheader("Ce que l'application détecte")
    st.caption(
        "Seuls les écarts qui se répètent sont signalés : une journée atypique "
        "n'a aucune importance."
    )
    render_alerts(report)

    if report.days:
        _render_charts(report, targets, window)
        _render_table(report, targets)

    st.divider()
    _render_manual_log(profile, today)
    st.divider()
    _render_logs(store, today, window)


def _render_charts(report, targets, window: int) -> None:
    st.subheader(f"Évolution sur {window} jours")

    frame = pd.DataFrame(
        [
            {
                "Jour": day.day.strftime("%d/%m"),
                "Calories": round(day.facts.kcal),
                "Objectif": round(targets.kcal),
                "Protéines": round(day.facts.protein),
                "Glucides": round(day.facts.carbs),
                "Lipides": round(day.facts.fat),
                "Fibres": round(day.facts.fiber, 1),
            }
            for day in report.days
        ]
    ).set_index("Jour")

    col1, col2 = st.columns(2)
    with col1:
        st.caption("Calories vs objectif")
        st.line_chart(frame[["Calories", "Objectif"]])
    with col2:
        st.caption("Macronutriments (g)")
        st.bar_chart(frame[["Protéines", "Glucides", "Lipides"]])

    suffix = " (journée en cours exclue)" if report.day_in_progress else ""
    st.caption(
        f"{report.logged_days} journée(s) analysée(s){suffix} — "
        f"{report.adherence * 100:.0f} % des nutriments suivis sont dans la cible."
    )


def _render_table(report, targets) -> None:
    with st.expander("Détail moyenne / objectif par nutriment"):
        st.dataframe(
            pd.DataFrame(trend_table(report, targets)),
            hide_index=True,
            width="stretch",
        )


def _render_manual_log(profile, today: date) -> None:
    st.subheader("Ajouter un repas à la main")
    st.caption("Pour un plat cuisiné hors suggestion, ou un repas pris à l'extérieur.")

    meals = meal_targets_for(profile)
    tab_recipe, tab_free = st.tabs(["Depuis une recette", "Saisie libre"])

    with tab_recipe:
        with st.form("log_recipe"):
            col1, col2, col3, col4 = st.columns([3, 1.2, 1.6, 1.4])
            recipe = col1.selectbox(
                "Recette", RECIPES, format_func=lambda r: r.name
            )
            portions = col2.number_input("Portions", 0.25, 4.0, 1.0, step=0.25)
            meal_key = col3.selectbox(
                "Repas", [m.key for m in meals],
                format_func=lambda key: MEAL_LABELS.get(key, key),
            )
            day = col4.date_input("Jour", value=today, format="DD/MM/YYYY")
            facts = recipe_facts(recipe, portions)
            st.caption(
                f"{facts.kcal:.0f} kcal · P {facts.protein:.0f} g · "
                f"G {facts.carbs:.0f} g · L {facts.fat:.0f} g"
            )
            if st.form_submit_button("Enregistrer", type="primary"):
                get_store().add_log(
                    MealLog(
                        day=day, meal=meal_key, label=recipe.name, facts=facts,
                        recipe_id=recipe.id, portions=portions,
                    )
                )
                st.toast("Repas enregistré.")
                refresh()

    with tab_free:
        with st.form("log_free"):
            col1, col2, col3 = st.columns([3, 1.6, 1.4])
            label = col1.text_input("Intitulé", placeholder="Restaurant, sandwich...")
            meal_key = col2.selectbox(
                "Repas", [m.key for m in meals],
                format_func=lambda key: MEAL_LABELS.get(key, key),
                key="free_meal",
            )
            day = col3.date_input("Jour", value=today, format="DD/MM/YYYY", key="free_day")
            col_a, col_b, col_c, col_d = st.columns(4)
            kcal = col_a.number_input("Calories", 0.0, 3000.0, 600.0, step=25.0)
            protein = col_b.number_input("Protéines (g)", 0.0, 300.0, 30.0, step=5.0)
            carbs = col_c.number_input("Glucides (g)", 0.0, 500.0, 60.0, step=5.0)
            fat = col_d.number_input("Lipides (g)", 0.0, 200.0, 20.0, step=2.0)
            st.caption(
                "Les micronutriments d'une saisie libre sont inconnus : ce repas "
                "compte dans les calories et les macros, pas dans la détection "
                "de carences en vitamines et minéraux."
            )
            if st.form_submit_button("Enregistrer", type="primary"):
                get_store().add_log(
                    MealLog(
                        day=day, meal=meal_key,
                        label=label or "Repas libre",
                        facts=NutritionFacts(
                            kcal=kcal, protein=protein, carbs=carbs, fat=fat
                        ),
                    )
                )
                st.toast("Repas enregistré.")
                refresh()


def _render_logs(store, today: date, window: int) -> None:
    st.subheader("Historique détaillé")
    logs = store.list_logs(start=today - timedelta(days=window - 1), end=today)
    if not logs:
        st.caption("Aucun repas enregistré sur la période.")
        return

    for log in logs:
        col1, col2, col3 = st.columns([2.2, 3, 0.8])
        col1.markdown(
            f"**{log.day.strftime('%d/%m')}** · {MEAL_LABELS.get(log.meal, log.meal)}"
        )
        col2.markdown(
            f"{log.label} — {log.facts.kcal:.0f} kcal · P {log.facts.protein:.0f} g · "
            f"G {log.facts.carbs:.0f} g · L {log.facts.fat:.0f} g"
        )
        if col3.button("Supprimer", key=f"hist_del_{log.id}"):
            store.delete_log(log.id)
            refresh()
