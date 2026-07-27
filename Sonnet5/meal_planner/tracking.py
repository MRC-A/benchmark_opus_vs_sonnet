"""Analyse de l'historique de repas pour détecter des carences ou
déséquilibres récurrents sur une fenêtre glissante (7 jours par défaut).

L'utilisateur ne voit que des messages d'alerte clairs ; les seuils et
calculs restent internes.
"""

from collections import defaultdict
from datetime import date, timedelta

from . import storage
from .macros import calculate_daily_macros

WINDOW_DAYS = 7
DEFICIENCY_RATIO_THRESHOLD = 0.8  # en dessous de 80% de la cible -> jour "insuffisant"
MIN_DAYS_LOGGED_FOR_ANALYSIS = 3  # pas assez de données -> pas d'alerte
MIN_DEFICIENT_DAYS_TO_FLAG = 4  # sur la fenêtre, nombre de jours insuffisants pour déclencher une alerte

NUTRIENT_LABELS = {
    "protein_g": "protéines",
    "fat_g": "lipides",
    "fiber_g": "fibres",
}


def _daily_targets(profile) -> dict:
    daily = calculate_daily_macros(profile)
    return {
        "protein_g": daily["protein_g"],
        "fat_g": daily["fat_g"],
        "fiber_g": daily["fiber_g"],
    }


def analyze_deficiencies(profile, today: date = None) -> list:
    """Retourne une liste de messages d'alerte (str) sur les carences
    récurrentes détectées sur les WINDOW_DAYS derniers jours. Liste vide
    si aucun déséquilibre notable ou pas assez de données."""
    if profile is None:
        return []

    today = today or date.today()
    window_start = today - timedelta(days=WINDOW_DAYS - 1)
    logs = storage.get_logs(window_start, today)

    if not logs:
        return []

    totals_by_day = defaultdict(lambda: {"protein_g": 0.0, "fat_g": 0.0, "fiber_g": 0.0})
    for entry in logs:
        day_totals = totals_by_day[entry.log_date]
        day_totals["protein_g"] += entry.protein_g
        day_totals["fat_g"] += entry.fat_g
        day_totals["fiber_g"] += entry.fiber_g

    days_logged = len(totals_by_day)
    if days_logged < MIN_DAYS_LOGGED_FOR_ANALYSIS:
        return []

    targets = _daily_targets(profile)
    alerts = []
    for nutrient, target in targets.items():
        deficient_days = sum(
            1 for day_totals in totals_by_day.values()
            if day_totals[nutrient] < target * DEFICIENCY_RATIO_THRESHOLD
        )
        if deficient_days >= min(MIN_DEFICIENT_DAYS_TO_FLAG, days_logged):
            label = NUTRIENT_LABELS[nutrient]
            alerts.append(
                f"Apport en {label} insuffisant sur {deficient_days} des {days_logged} "
                f"derniers jours suivis (objectif ≈ {round(target)} g/jour). "
                f"Pense à enrichir tes repas en {label} sur les prochains jours."
            )

    return alerts
