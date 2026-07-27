"""Page « Mes aliments » : saisie du garde-manger et des dates de péremption."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from mealplanner.foods import CATEGORIES, FOODS, foods_by_category
from mealplanner.pantry import build_lots, describe_lot, expiring_soon
from mealplanner.substitutions import substitutes_catalog

from .shared import get_store, refresh


def render() -> None:
    st.header("Mes aliments")
    st.caption(
        "Indiquez ce que vous avez chez vous. La date de péremption est "
        "facultative — quand elle est là, l'application s'en sert pour vous "
        "proposer en priorité les plats qui évitent le gaspillage."
    )

    store = get_store()
    items = store.list_pantry()
    lots = build_lots(items, include_expired=True)

    _render_add_form()
    st.divider()

    urgent = expiring_soon(lots, within_days=3)
    expired = [lot for lot in lots if lot.expired]
    if expired:
        st.error(
            "**À jeter :** " + " · ".join(describe_lot(lot) for lot in expired)
        )
        if st.button("Retirer les produits périmés"):
            removed = store.purge_expired()
            st.toast(f"{removed} produit(s) retiré(s).")
            refresh()
    if urgent:
        st.warning(
            "**À consommer en priorité :** "
            + " · ".join(describe_lot(lot) for lot in urgent)
        )

    if not items:
        st.info("Votre garde-manger est vide. Ajoutez un premier aliment ci-dessus.")
        _render_starter_button()
        return

    _render_table(items)


def _render_add_form() -> None:
    grouped = foods_by_category()
    with st.form("add_pantry", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns([3, 1.4, 1.6, 1])
        with col1:
            category = st.selectbox(
                "Rayon", list(CATEGORIES), format_func=lambda key: CATEGORIES[key]
            )
            options = grouped.get(category, [])
            food = st.selectbox(
                "Aliment", options, format_func=lambda f: f.name
            ) if options else None
        with col2:
            grams = st.number_input("Quantité (g)", 10.0, 10000.0, 200.0, step=10.0)
        with col3:
            has_expiry = st.checkbox("Date de péremption", value=False)
            expiry = st.date_input(
                "Périme le",
                value=date.today() + timedelta(days=5),
                format="DD/MM/YYYY",
                label_visibility="collapsed",
                disabled=not has_expiry,
            )
        with col4:
            st.write("")
            st.write("")
            submitted = st.form_submit_button("Ajouter", type="primary")

        if food and food.unit_grams:
            st.caption(
                f"Repère : {food.unit_label} ≈ {food.unit_grams:.0f} g. "
                f"Remplaçants habituels : {', '.join(substitutes_catalog(food.id, 3))}."
            )

    if submitted and food:
        get_store().add_pantry_item(
            food.id, float(grams), expiry if has_expiry else None
        )
        st.toast(f"{food.name} ajouté ({grams:.0f} g).")
        refresh()


def _render_table(items) -> None:
    st.subheader("Contenu du garde-manger")
    st.caption("Modifiez les quantités ou les dates directement dans le tableau.")

    frame = pd.DataFrame(
        [
            {
                "Aliment": FOODS[item.food_id].name if item.food_id in FOODS else item.food_id,
                "Rayon": CATEGORIES.get(
                    FOODS[item.food_id].category if item.food_id in FOODS else "autre",
                    "Autres",
                ),
                "Quantité (g)": float(item.grams),
                "Péremption": item.expiry,
                "Supprimer": False,
            }
            for item in items
        ]
    )

    edited = st.data_editor(
        frame,
        hide_index=True,
        num_rows="fixed",
        width="stretch",
        column_config={
            "Aliment": st.column_config.TextColumn(disabled=True),
            "Rayon": st.column_config.TextColumn(disabled=True),
            "Quantité (g)": st.column_config.NumberColumn(
                min_value=0.0, step=10.0, format="%.0f"
            ),
            "Péremption": st.column_config.DateColumn(format="DD/MM/YYYY"),
            "Supprimer": st.column_config.CheckboxColumn(help="Cocher puis enregistrer"),
        },
        key="pantry_editor",
    )

    col1, col2 = st.columns([1, 4])
    if col1.button("Enregistrer les modifications", type="primary"):
        _apply_edits(items, edited)
        refresh()
    if col2.button("Vider le garde-manger"):
        get_store().clear_pantry()
        st.toast("Garde-manger vidé.")
        refresh()


def _apply_edits(items, edited: pd.DataFrame) -> None:
    """Réécrit les lignes modifiées ; l'ordre du tableau suit celui des lots."""
    store = get_store()
    changes = 0
    for item, (_, row) in zip(items, edited.iterrows()):
        if bool(row["Supprimer"]) or float(row["Quantité (g)"]) <= 0:
            store.delete_pantry_item(item.id)
            changes += 1
            continue
        new_expiry = row["Péremption"]
        if isinstance(new_expiry, pd.Timestamp):
            new_expiry = new_expiry.date()
        elif new_expiry is not None and not isinstance(new_expiry, date):
            new_expiry = None
        if pd.isna(row["Péremption"]):
            new_expiry = None
        if abs(float(row["Quantité (g)"]) - item.grams) > 0.01 or new_expiry != item.expiry:
            store.update_pantry_item(item.id, float(row["Quantité (g)"]), new_expiry)
            changes += 1
    st.toast(f"{changes} ligne(s) mise(s) à jour.")


# Jeu de départ : permet d'essayer les suggestions sans dix minutes de saisie.
_STARTER = (
    ("poulet_blanc", 500, 2),
    ("oeuf", 360, 12),
    ("saumon", 260, 4),
    ("riz_blanc", 1000, None),
    ("pates_completes", 500, None),
    ("flocons_avoine", 800, None),
    ("patate_douce", 600, 15),
    ("brocoli", 400, 5),
    ("haricots_verts", 400, 8),
    ("courgette", 300, 6),
    ("tomate", 400, 4),
    ("oignon", 300, 30),
    ("skyr", 450, 9),
    ("fromage_blanc_0", 500, 10),
    ("banane", 480, 5),
    ("beurre_cacahuete", 350, None),
    ("huile_olive", 500, None),
    ("lentilles", 500, None),
)


def _render_starter_button() -> None:
    if st.button("Remplir avec un garde-manger d'exemple"):
        store = get_store()
        today = date.today()
        for food_id, grams, days in _STARTER:
            store.add_pantry_item(
                food_id, grams, today + timedelta(days=days) if days else None
            )
        st.toast("Garde-manger d'exemple chargé.")
        refresh()
