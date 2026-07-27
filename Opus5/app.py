"""Point d'entrée de l'application.

Lancement :
    streamlit run app.py
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import streamlit as st

# Permet de lancer `streamlit run app.py` depuis n'importe quel dossier.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mealplanner.models import NutritionFacts  # noqa: E402
from ui import page_history, page_pantry, page_profile, page_suggest, page_today  # noqa: E402
from ui.shared import get_store, load_profile, targets_for  # noqa: E402

PAGES = {
    "Aujourd'hui": ("🏠", page_today.render),
    "Suggestions": ("🍽️", page_suggest.render),
    "Mes aliments": ("🧺", page_pantry.render),
    "Suivi": ("📈", page_history.render),
    "Profil": ("👤", page_profile.render),
}


def main() -> None:
    st.set_page_config(
        page_title="Assiette — planificateur de repas",
        page_icon="🥗",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    with st.sidebar:
        st.title("🥗 Assiette")
        st.caption("Vos repas, calculés pour vous.")
        choice = st.radio(
            "Navigation",
            list(PAGES),
            format_func=lambda name: f"{PAGES[name][0]}  {name}",
            label_visibility="collapsed",
        )
        _render_sidebar_summary()

    PAGES[choice][1]()


def _render_sidebar_summary() -> None:
    profile = load_profile()
    if profile is None:
        st.divider()
        st.caption("Profil non renseigné.")
        return

    targets = targets_for(profile)
    logs = get_store().logs_for_day(date.today())
    consumed = NutritionFacts.sum(log.facts for log in logs)
    remaining = max(targets.kcal - consumed.kcal, 0.0)

    st.divider()
    st.metric("Restant aujourd'hui", f"{remaining:.0f} kcal")
    st.progress(min(consumed.kcal / targets.kcal, 1.0) if targets.kcal else 0.0)
    st.caption(
        f"{consumed.kcal:.0f} / {targets.kcal:.0f} kcal · "
        f"P {consumed.protein:.0f}/{targets.protein:.0f} g"
    )
    st.divider()
    st.caption("Données stockées localement dans `data/mealplanner.db`.")


if __name__ == "__main__":
    main()
