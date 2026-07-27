"""Utilitaires partagés par les pages Streamlit.

Cette couche est la seule à connaître Streamlit. Elle ne contient aucune règle
nutritionnelle : elle se contente de lire le paquet `mealplanner` et de le
mettre en forme.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

import streamlit as st

from mealplanner import nutrition
from mealplanner.analytics import WINDOW_DAYS, WindowReport, analyse_window
from mealplanner.models import NutritionFacts, Profile
from mealplanner.nutrition import DailyTargets, MealTarget
from mealplanner.pantry import Lot, build_lots
from mealplanner.storage import Store


@st.cache_resource(show_spinner=False)
def get_store() -> Store:
    """Connexion unique à la base locale, réutilisée entre les rerenders."""
    return Store()


def load_profile() -> Optional[Profile]:
    return get_store().load_profile()


def require_profile() -> Optional[Profile]:
    """Renvoie le profil, ou invite à le créer et interrompt la page."""
    profile = load_profile()
    if profile is None:
        st.info(
            "Commencez par renseigner votre profil dans l'onglet **Profil** : "
            "tout le reste de l'application en découle."
        )
        st.stop()
    return profile


def targets_for(profile: Profile) -> DailyTargets:
    return nutrition.daily_targets(profile)


def meal_targets_for(profile: Profile) -> list[MealTarget]:
    return nutrition.split_by_meal(nutrition.daily_targets(profile), profile.meals_per_day)


def current_lots(today: Optional[date] = None) -> list[Lot]:
    return build_lots(get_store().list_pantry(), today or date.today())


def week_report(
    profile: Profile,
    end_day: Optional[date] = None,
    window_days: int = WINDOW_DAYS,
) -> WindowReport:
    end_day = end_day or date.today()
    return analyse_window(
        get_store().list_logs(),
        targets_for(profile),
        end_day=end_day,
        window_days=window_days,
    )


def default_meal_key(profile: Profile) -> str:
    """Repas le plus probable en fonction de l'heure."""
    keys = [meal.key for meal in meal_targets_for(profile)]
    hour = datetime.now().hour
    if hour < 10 and "petit_dej" in keys:
        return "petit_dej"
    if hour < 11 and "collation_matin" in keys:
        return "collation_matin"
    if hour < 14 and "dejeuner" in keys:
        return "dejeuner"
    if hour < 18 and "collation" in keys:
        return "collation"
    return "diner" if "diner" in keys else keys[-1]


# --------------------------------------------------------------------------- #
# Mise en forme
# --------------------------------------------------------------------------- #

_JOURS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
_MOIS = (
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
)


def long_date(day: date) -> str:
    """Date en français, sans dépendre de la locale du système."""
    return f"{_JOURS[day.weekday()]} {day.day} {_MOIS[day.month - 1]} {day.year}".capitalize()


def macro_line(facts: NutritionFacts) -> str:
    return (
        f"**{facts.kcal:.0f}** kcal · "
        f"P {facts.protein:.0f} g · G {facts.carbs:.0f} g · L {facts.fat:.0f} g"
    )


def progress_row(label: str, current: float, target: float, unit: str = "g") -> None:
    """Barre de progression avec valeur chiffrée, tolérante au dépassement."""
    ratio = 0.0 if target <= 0 else current / target
    st.caption(f"{label} — {current:.0f} / {target:.0f} {unit}  ({ratio * 100:.0f} %)")
    st.progress(min(max(ratio, 0.0), 1.0))


def severity_style(severity: str) -> tuple[str, str]:
    return {
        "critique": ("🔴", "error"),
        "attention": ("🟠", "warning"),
        "info": ("🔵", "info"),
    }.get(severity, ("🔵", "info"))


def render_alerts(report: WindowReport, compact: bool = False) -> None:
    """Affiche les alertes de la fenêtre glissante."""
    if not report.has_enough_data:
        st.info(
            f"Encore un peu de patience : il faut au moins 3 journées loggées "
            f"pour détecter des tendances fiables "
            f"({report.logged_days} pour l'instant)."
        )
        return
    if not report.alerts:
        st.success(
            "Aucun déséquilibre récurrent détecté sur les 7 derniers jours. "
            "Continuez comme ça."
        )
        return

    if report.day_in_progress and not compact:
        st.caption(
            "La journée en cours est encore incomplète : elle est exclue du "
            "diagnostic pour ne pas fausser les moyennes."
        )

    for alert in report.alerts:
        icon, kind = severity_style(alert.severity)
        body = f"{icon} **{alert.label}** — {alert.message}"
        if not compact:
            body += f"\n\n💡 {alert.advice}"
            if alert.foods:
                body += f"\n\n🥗 Sources à privilégier : {', '.join(alert.foods)}."
        getattr(st, kind)(body)


def refresh() -> None:
    """Force un rerender après une écriture en base."""
    st.rerun()
