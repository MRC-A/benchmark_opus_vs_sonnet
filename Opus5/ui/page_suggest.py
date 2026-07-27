"""Page « Suggestions » : propose des plats adaptés au repas et au garde-manger."""

from __future__ import annotations

from datetime import date

import streamlit as st

from mealplanner.models import MealLog
from mealplanner.nutrition import MealTarget
from mealplanner.suggester import Suggestion, plan_day, suggest

from .shared import (
    current_lots,
    default_meal_key,
    get_store,
    macro_line,
    meal_targets_for,
    refresh,
    require_profile,
)


def render() -> None:
    profile = require_profile()
    st.header("Que puis-je manger ?")

    lots = current_lots()
    meals = meal_targets_for(profile)
    if not lots:
        st.info(
            "Ajoutez d'abord quelques aliments dans l'onglet **Mes aliments** : "
            "les suggestions sont calculées à partir de ce que vous avez."
        )

    keys = [meal.key for meal in meals]
    default_index = keys.index(default_meal_key(profile)) if default_meal_key(profile) in keys else 0

    col1, col2, col3 = st.columns([2, 1.4, 1.4])
    with col1:
        meal = st.selectbox(
            "Repas", meals, index=default_index, format_func=lambda m: m.label
        )
    with col2:
        only_cookable = st.toggle(
            "Réalisable sans courses", value=False,
            help="N'afficher que les plats dont vous avez tous les ingrédients.",
        )
    with col3:
        day = st.date_input("Journée", value=date.today(), format="DD/MM/YYYY")

    st.caption(f"Objectif de ce repas — {macro_line(meal.as_facts())}")

    recent = get_store().recent_recipe_ids(since=day.fromordinal(day.toordinal() - 2))
    suggestions = suggest(
        target=meal.as_facts(),
        lots=lots,
        meal_key=meal.key,
        limit=3,
        recent_recipe_ids=recent,
        only_cookable=only_cookable,
    )

    if not suggestions:
        st.warning(
            "Aucun plat réalisable avec le stock actuel. Décochez « réalisable "
            "sans courses » pour voir les propositions avec substitutions."
        )
    for index, suggestion in enumerate(suggestions):
        render_suggestion(suggestion, meal, day, key=f"sugg_{meal.key}_{index}")

    st.divider()
    _render_day_plan(profile, lots, day)


def render_suggestion(
    suggestion: Suggestion,
    meal: MealTarget,
    day: date,
    key: str,
    expanded: bool = True,
) -> None:
    """Carte détaillée d'une proposition, avec bouton de validation."""
    badge = "✅ prêt à cuisiner" if suggestion.cookable_now else "🛒 1 ou 2 ingrédients à remplacer"
    with st.expander(
        f"**{suggestion.recipe.name}** — {suggestion.portions:.2f} portion(s) · {badge}",
        expanded=expanded,
    ):
        col1, col2 = st.columns([1.3, 1])

        with col1:
            st.markdown(macro_line(suggestion.facts))
            delta = suggestion.delta()
            st.caption(
                f"Écart à l'objectif du repas : {delta.kcal:+.0f} kcal · "
                f"P {delta.protein:+.0f} g · G {delta.carbs:+.0f} g · L {delta.fat:+.0f} g"
                f"  —  ⏱ {suggestion.recipe.prep_minutes} min"
            )
            for note in suggestion.notes:
                st.caption(f"• {note}")

            st.markdown("**Ingrédients**")
            for ing in suggestion.ingredients:
                suffix = " *(facultatif)*" if ing.optional else ""
                if ing.covered:
                    urgency = ""
                    if ing.days_left is not None and ing.days_left <= 3:
                        urgency = (
                            " ⏳ à consommer vite"
                            if ing.days_left > 0 else " ⏳ aujourd'hui"
                        )
                    st.markdown(f"- {ing.food.name} — {ing.grams:.0f} g{suffix}{urgency}")
                else:
                    line = f"- ❌ {ing.food.name} — {ing.grams:.0f} g{suffix}"
                    if ing.from_pantry > 0:
                        line += f" (vous n'en avez que {ing.from_pantry:.0f} g)"
                    st.markdown(line)
                    if ing.substitution:
                        st.markdown(
                            f"    ↳ **Remplacer par** {ing.substitution.replacement.name} "
                            f"({ing.substitution.grams:.0f} g) — "
                            f"{'déjà chez vous' if ing.substitution.in_pantry else 'à acheter'}"
                        )
                    else:
                        st.markdown("    ↳ *aucun remplacement évident, à acheter*")

        with col2:
            st.markdown("**Préparation**")
            for step_index, step in enumerate(suggestion.recipe.steps, start=1):
                st.markdown(f"{step_index}. {step}")
            if suggestion.recipe.tags:
                st.caption(" · ".join(f"`{tag}`" for tag in suggestion.recipe.tags))

        consume = st.checkbox(
            "Déduire les ingrédients de mon garde-manger",
            value=True, key=f"{key}_consume",
        )
        if st.button("J'ai mangé ce plat", key=f"{key}_log", type="primary"):
            log_suggestion(suggestion, meal.key, day, consume)
            st.toast(f"{suggestion.recipe.name} enregistré.")
            refresh()


def log_suggestion(
    suggestion: Suggestion, meal_key: str, day: date, consume: bool
) -> None:
    """Enregistre le repas et, si demandé, décrémente le garde-manger."""
    store = get_store()
    store.add_log(
        MealLog(
            day=day,
            meal=meal_key,
            label=suggestion.recipe.name,
            facts=suggestion.facts,
            recipe_id=suggestion.recipe.id,
            portions=suggestion.portions,
        )
    )
    if not consume:
        return

    consumption: list[tuple[str, float]] = []
    for ing in suggestion.ingredients:
        if ing.from_pantry > 0:
            consumption.append((ing.food.id, ing.from_pantry))
        if ing.substitution and ing.substitution.in_pantry:
            consumption.append((ing.substitution.replacement.id, ing.substitution.grams))
    store.consume(consumption)


def _render_day_plan(profile, lots, day: date) -> None:
    st.subheader("Composer toute la journée")
    st.caption(
        "Un plat par repas, choisis pour couvrir vos macros sans répéter deux "
        "fois le même plat."
    )
    if not st.button("Proposer une journée complète"):
        return

    meals = meal_targets_for(profile)
    plan = plan_day(meals, lots)
    for meal in meals:
        suggestion = plan.get(meal.key)
        st.markdown(f"### {meal.label}")
        if suggestion is None:
            st.caption("Aucune proposition disponible.")
            continue
        render_suggestion(
            suggestion, meal, day, key=f"plan_{meal.key}", expanded=False
        )
