"""Analyse du suivi sur 7 jours glissants.

Principe : un écart ponctuel n'est pas un problème, une habitude en est un.
On ne signale donc jamais une journée isolée. Pour chaque nutriment on compare
l'apport quotidien à l'objectif, et on ne remonte une alerte que si l'écart se
répète sur une part significative des journées effectivement renseignées.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from statistics import mean, pstdev
from typing import Iterable, Optional, Sequence

from .foods import richest_in
from .models import MealLog, NutritionFacts
from .nutrition import DailyTargets
from .recipes import recipe_name

WINDOW_DAYS = 7
# Nombre minimum de journées renseignées avant d'oser un diagnostic.
MIN_LOGGED_DAYS = 3
# Part des journées concernées à partir de laquelle l'écart devient « récurrent ».
RECURRENCE_RATIO = 0.6

LOW_THRESHOLD = 0.85  # sous 85% de l'objectif : apport insuffisant
HIGH_THRESHOLD = 1.15  # au-delà de 115% : apport excessif

# Nutriments surveillés, avec leur seuil bas spécifique et le sens de l'alerte.
@dataclass(frozen=True)
class Watch:
    key: str
    label: str
    unit: str
    low: float
    high: Optional[float]
    advice: str


WATCHED: tuple[Watch, ...] = (
    Watch("kcal", "Calories", "kcal", 0.85, 1.15,
          "Ajustez les portions de féculents, c'est le levier le plus simple."),
    Watch("protein", "Protéines", "g", 0.90, None,
          "Ajoutez une source protéique à chaque repas, y compris au petit-déjeuner."),
    Watch("carbs", "Glucides", "g", 0.80, 1.25,
          "Les glucides pilotent l'énergie à l'entraînement : jouez sur riz, pâtes et flocons."),
    Watch("fat", "Lipides", "g", 0.80, 1.25,
          "Des lipides trop bas sur la durée pèsent sur l'équilibre hormonal."),
    Watch("fiber", "Fibres", "g", 0.80, None,
          "Visez légumes à chaque repas + une source complète (légumineuses, céréales complètes)."),
    Watch("iron", "Fer", "mg", 0.80, None,
          "Associez une source de fer à de la vitamine C, qui en améliore l'absorption."),
    Watch("calcium", "Calcium", "mg", 0.80, None,
          "Produits laitiers, tofu ou eaux minérales calciques comblent vite l'écart."),
    Watch("vitamin_c", "Vitamine C", "mg", 0.80, None,
          "Un fruit cru ou des légumes peu cuits par jour suffisent généralement."),
    Watch("magnesium", "Magnésium", "mg", 0.80, None,
          "Oléagineux, céréales complètes et chocolat noir sont les sources les plus denses."),
    Watch("omega3", "Oméga-3 (ALA)", "g", 0.70, None,
          "Une cuillère d'huile de colza ou de noix par jour couvre l'essentiel."),
)


@dataclass(frozen=True)
class DayTotals:
    day: date
    facts: NutritionFacts
    meals: int


@dataclass(frozen=True)
class Alert:
    key: str
    label: str
    unit: str
    kind: str  # "deficit" | "exces" | "regularite" | "monotonie"
    severity: str  # "info" | "attention" | "critique"
    mean_ratio: float
    affected_days: int
    logged_days: int
    message: str
    advice: str
    foods: tuple[str, ...] = ()


@dataclass
class WindowReport:
    start: date
    end: date
    logged_days: int
    days: list[DayTotals] = field(default_factory=list)
    averages: NutritionFacts = field(default_factory=NutritionFacts)
    ratios: dict[str, float] = field(default_factory=dict)
    alerts: list[Alert] = field(default_factory=list)
    has_enough_data: bool = False
    adherence: float = 0.0  # part des nutriments dans la cible, 0 à 1
    # Vrai lorsque la journée en cours a été écartée du diagnostic.
    day_in_progress: bool = False


def daily_totals(logs: Iterable[MealLog]) -> dict[date, DayTotals]:
    """Agrège les repas loggés par journée."""
    buckets: dict[date, list[MealLog]] = {}
    for log in logs:
        buckets.setdefault(log.day, []).append(log)
    return {
        day: DayTotals(
            day=day,
            facts=NutritionFacts.sum(log.facts for log in items),
            meals=len(items),
        )
        for day, items in buckets.items()
    }


def _severity(ratio: float, low: float) -> str:
    if ratio < low * 0.7:
        return "critique"
    if ratio < low * 0.9:
        return "attention"
    return "info"


def _phrase_deficit(ratio: float, affected: int, logged: int) -> str:
    pct = round((1 - ratio) * 100)
    return (
        f"en retrait d'environ {pct}% sur la période "
        f"({affected} journée(s) sur {logged} sous l'objectif)."
    )


def _phrase_excess(ratio: float, affected: int, logged: int) -> str:
    pct = round((ratio - 1) * 100)
    return (
        f"au-dessus de l'objectif d'environ {pct}% "
        f"({affected} journée(s) sur {logged})."
    )


def _drop_day_in_progress(days: list[DayTotals], end_day: date) -> tuple[list[DayTotals], bool]:
    """Écarte la journée en cours tant qu'elle est manifestement incomplète.

    Sans cela, un seul repas logué à midi ferait apparaître un « déficit »
    quotidien parfaitement normal, et tous les diagnostics deviendraient faux.
    """
    if len(days) < 2 or days[-1].day != end_day:
        return days, False
    others = [day.meals for day in days[:-1]]
    typical = sorted(others)[len(others) // 2]
    if days[-1].meals < typical:
        return days[:-1], True
    return days, False


def analyse_window(
    logs: Sequence[MealLog],
    targets: DailyTargets,
    end_day: Optional[date] = None,
    window_days: int = WINDOW_DAYS,
) -> WindowReport:
    """Analyse la fenêtre glissante et remonte les déséquilibres récurrents."""
    end_day = end_day or date.today()
    start_day = end_day - timedelta(days=window_days - 1)
    window_logs = [log for log in logs if start_day <= log.day <= end_day]

    totals = daily_totals(window_logs)
    all_days = [totals[day] for day in sorted(totals)]
    report = WindowReport(
        start=start_day, end=end_day, logged_days=len(all_days), days=all_days
    )

    if not all_days:
        return report

    days, report.day_in_progress = _drop_day_in_progress(all_days, end_day)
    report.logged_days = len(days)
    if not days:
        return report

    report.averages = NutritionFacts(
        **{
            key: mean(getattr(day.facts, key) for day in days)
            for key in NutritionFacts().as_dict()
        }
    )
    report.ratios = {
        watch.key: (
            getattr(report.averages, watch.key) / getattr(targets, watch.key)
            if getattr(targets, watch.key) > 0 else 0.0
        )
        for watch in WATCHED
    }

    if len(days) < MIN_LOGGED_DAYS:
        # Pas assez de matière : on affiche les moyennes, mais aucun diagnostic.
        return report

    report.has_enough_data = True
    in_range = 0
    for watch in WATCHED:
        target_value = getattr(targets, watch.key)
        if target_value <= 0:
            continue
        ratios = [getattr(day.facts, watch.key) / target_value for day in days]
        mean_ratio = mean(ratios)
        if watch.low <= mean_ratio <= (watch.high or HIGH_THRESHOLD):
            in_range += 1

        low_days = sum(1 for r in ratios if r < watch.low)
        if low_days >= max(MIN_LOGGED_DAYS, round(len(days) * RECURRENCE_RATIO)):
            report.alerts.append(
                Alert(
                    key=watch.key,
                    label=watch.label,
                    unit=watch.unit,
                    kind="deficit",
                    severity=_severity(mean_ratio, watch.low),
                    mean_ratio=mean_ratio,
                    affected_days=low_days,
                    logged_days=len(days),
                    message=_phrase_deficit(mean_ratio, low_days, len(days)),
                    advice=watch.advice,
                    foods=tuple(f.name for f in richest_in(watch.key, 3))
                    if watch.key not in ("kcal", "carbs", "fat") else (),
                )
            )
            continue

        if watch.high:
            high_days = sum(1 for r in ratios if r > watch.high)
            if high_days >= max(MIN_LOGGED_DAYS, round(len(days) * RECURRENCE_RATIO)):
                report.alerts.append(
                    Alert(
                        key=watch.key,
                        label=watch.label,
                        unit=watch.unit,
                        kind="exces",
                        severity="attention" if mean_ratio > watch.high * 1.15 else "info",
                        mean_ratio=mean_ratio,
                        affected_days=high_days,
                        logged_days=len(days),
                        message=_phrase_excess(mean_ratio, high_days, len(days)),
                        advice=watch.advice,
                    )
                )

    report.adherence = in_range / len(WATCHED)
    analysed_days = {day.day for day in days}
    report.alerts.extend(
        _behaviour_alerts(days, [log for log in window_logs if log.day in analysed_days])
    )
    report.alerts.sort(key=lambda a: {"critique": 0, "attention": 1, "info": 2}[a.severity])
    return report


def _behaviour_alerts(days: Sequence[DayTotals], logs: Sequence[MealLog]) -> list[Alert]:
    """Alertes de comportement : irrégularité énergétique et monotonie."""
    alerts: list[Alert] = []

    kcal_values = [day.facts.kcal for day in days if day.facts.kcal > 0]
    if len(kcal_values) >= MIN_LOGGED_DAYS:
        average = mean(kcal_values)
        if average > 0:
            variation = pstdev(kcal_values) / average
            if variation > 0.25:
                alerts.append(
                    Alert(
                        key="regularite", label="Régularité", unit="",
                        kind="regularite", severity="info",
                        mean_ratio=1.0, affected_days=len(kcal_values),
                        logged_days=len(days),
                        message=(
                            f"Apports très irréguliers d'un jour à l'autre "
                            f"(± {variation * 100:.0f}% autour de la moyenne)."
                        ),
                        advice="Des journées plus stables facilitent la progression et la digestion.",
                    )
                )

    recipe_logs = [log.recipe_id for log in logs if log.recipe_id]
    if len(recipe_logs) >= 6:
        counts: dict[str, int] = {}
        for rid in recipe_logs:
            counts[rid] = counts.get(rid, 0) + 1
        top_id, top_count = max(counts.items(), key=lambda kv: kv[1])
        if top_count / len(recipe_logs) >= 0.4:
            alerts.append(
                Alert(
                    key="monotonie", label="Variété", unit="",
                    kind="monotonie", severity="info",
                    mean_ratio=top_count / len(recipe_logs),
                    affected_days=top_count, logged_days=len(days),
                    message=(
                        f"« {recipe_name(top_id)} » représente "
                        f"{top_count / len(recipe_logs) * 100:.0f}% de vos repas loggés."
                    ),
                    advice="Varier les sources limite les carences en micronutriments.",
                )
            )
    return alerts


def trend_table(report: WindowReport, targets: DailyTargets) -> list[dict]:
    """Tableau moyenne / objectif / écart, prêt à afficher."""
    rows = []
    for watch in WATCHED:
        target_value = getattr(targets, watch.key)
        if target_value <= 0:
            continue
        average = getattr(report.averages, watch.key)
        rows.append(
            {
                "Nutriment": watch.label,
                "Moyenne / jour": round(average, 1),
                "Objectif": round(target_value, 1),
                "Unité": watch.unit,
                "% objectif": round(average / target_value * 100),
            }
        )
    return rows
