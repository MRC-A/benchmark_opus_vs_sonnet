"""Page « Aujourd'hui » : où j'en suis, ce qu'il me reste à manger."""

from __future__ import annotations

from datetime import date

import streamlit as st

from mealplanner.models import NutritionFacts
from mealplanner.pantry import describe_lot, expiring_soon
from mealplanner.suggester import suggest

from .page_suggest import render_suggestion
from .shared import (
    current_lots,
    get_store,
    long_date,
    macro_line,
    meal_targets_for,
    progress_row,
    refresh,
    render_alerts,
    require_profile,
    targets_for,
    week_report,
)


def render() -> None:
    profile = require_profile()
    today = date.today()
    store = get_store()

    targets = targets_for(profile)
    meals = meal_targets_for(profile)
    logs = store.logs_for_day(today)
    consumed = NutritionFacts.sum(log.facts for log in logs)

    st.header("Aujourd'hui")
    st.caption(long_date(today))

    _render_totals(consumed, targets)
    st.divider()
    _render_meals(profile, meals, logs, today)
    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("À consommer en priorité")
        urgent = expiring_soon(current_lots(today), within_days=4)
        if urgent:
            for lot in urgent[:6]:
                st.markdown(f"- {describe_lot(lot)}")
            st.caption(
                "Ces aliments remontent automatiquement dans les suggestions de plats."
            )
        else:
            st.caption("Rien d'urgent dans votre garde-manger.")
    with col2:
        st.subheader("Tendance sur 7 jours")
        render_alerts(week_report(profile, today), compact=True)


def _render_totals(consumed: NutritionFacts, targets) -> None:
    remaining = max(targets.kcal - consumed.kcal, 0)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Calories", f"{consumed.kcal:.0f}", f"{consumed.kcal - targets.kcal:+.0f} kcal")
    col2.metric("Protéines", f"{consumed.protein:.0f} g", f"{consumed.protein - targets.protein:+.0f} g")
    col3.metric("Glucides", f"{consumed.carbs:.0f} g", f"{consumed.carbs - targets.carbs:+.0f} g")
    col4.metric("Lipides", f"{consumed.fat:.0f} g", f"{consumed.fat - targets.fat:+.0f} g")
    st.caption(
        f"Objectif du jour : {targets.kcal:.0f} kcal — il vous reste "
        f"**{remaining:.0f} kcal** à répartir."
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        progress_row("Protéines", consumed.protein, targets.protein)
    with col2:
        progress_row("Glucides", consumed.carbs, targets.carbs)
    with col3:
        progress_row("Lipides", consumed.fat, targets.fat)


def _render_meals(profile, meals, logs, today: date) -> None:
    st.subheader("Vos repas")
    logs_by_meal: dict[str, list] = {}
    for log in logs:
        logs_by_meal.setdefault(log.meal, []).append(log)

    lots = current_lots(today)
    recent = get_store().recent_recipe_ids(since=date.fromordinal(today.toordinal() - 2))

    for meal in meals:
        meal_logs = logs_by_meal.get(meal.key, [])
        eaten = NutritionFacts.sum(log.facts for log in meal_logs)
        done = "✅" if meal_logs else "⬜"

        with st.container(border=True):
            head, tail = st.columns([3, 2])
            with head:
                st.markdown(f"{done} **{meal.label}**")
                st.caption(f"Objectif — {macro_line(meal.as_facts())}")
                if meal_logs:
                    for log in meal_logs:
                        col_a, col_b = st.columns([4, 1])
                        col_a.markdown(
                            f"· {log.label} — {log.facts.kcal:.0f} kcal, "
                            f"P {log.facts.protein:.0f} g"
                        )
                        if col_b.button("Retirer", key=f"del_{log.id}"):
                            get_store().delete_log(log.id)
                            refresh()
                    st.caption(f"Consommé — {macro_line(eaten)}")
            with tail:
                if not meal_logs and st.button(
                    "Voir des idées", key=f"ideas_{meal.key}"
                ):
                    st.session_state[f"show_ideas_{meal.key}"] = True
                if meal_logs:
                    st.caption("Repas enregistré.")

            if st.session_state.get(f"show_ideas_{meal.key}"):
                remaining_target = meal.as_facts() - eaten
                # En dessous de ce reliquat, aucune recette du catalogue ne peut
                # descendre assez bas : mieux vaut le dire que proposer un plat
                # deux fois trop copieux.
                if remaining_target.kcal < max(150.0, meal.kcal * 0.35):
                    st.caption(
                        f"Objectif de ce repas quasiment atteint — il ne reste que "
                        f"{max(remaining_target.kcal, 0):.0f} kcal. Un fruit ou un "
                        f"yaourt suffit à compléter."
                    )
                else:
                    options = suggest(
                        target=remaining_target, lots=lots, meal_key=meal.key,
                        limit=2, recent_recipe_ids=recent,
                    )
                    for index, option in enumerate(options):
                        render_suggestion(
                            option, meal, today,
                            key=f"today_{meal.key}_{index}", expanded=index == 0,
                        )
                    if st.button("Masquer", key=f"hide_{meal.key}"):
                        st.session_state[f"show_ideas_{meal.key}"] = False
                        refresh()
