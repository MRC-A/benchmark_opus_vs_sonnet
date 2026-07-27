"""Tests de la logique métier (bibliothèque standard uniquement).

    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mealplanner import analytics, nutrition, pantry, substitutions, suggester
from mealplanner.foods import FOODS, get_food
from mealplanner.models import MealLog, NutritionFacts, PantryItem, Profile
from mealplanner.recipes import RECIPES, RECIPES_BY_ID, recipe_facts
from mealplanner.storage import Store

TODAY = date(2025, 6, 15)

ATHLETE = Profile(weight_kg=80, height_cm=180, age=28, sex="homme",
                  activity="intense", goal="prise_de_masse", meals_per_day=4)
SEDENTARY = Profile(weight_kg=80, height_cm=180, age=28, sex="homme",
                    activity="sedentaire", goal="maintien", meals_per_day=3)


class TestNutrition(unittest.TestCase):
    def test_bmr_mifflin(self):
        # 10*80 + 6.25*180 - 5*28 + 5 = 1790
        self.assertAlmostEqual(nutrition.bmr(ATHLETE), 1790.0, places=1)
        # La formule femme retire 166 kcal par rapport à la formule homme.
        self.assertAlmostEqual(
            nutrition.bmr(ATHLETE.with_(sex="femme")), 1790.0 - 166.0, places=1
        )

    def test_athlete_needs_more_than_sedentary(self):
        athlete = nutrition.daily_targets(ATHLETE)
        sedentary = nutrition.daily_targets(SEDENTARY)
        self.assertGreater(athlete.kcal, sedentary.kcal * 1.3)
        self.assertGreater(athlete.protein, sedentary.protein * 1.5)

    def test_goal_sets_are_disjoint(self):
        athlete_goals = set(nutrition.goals_for("intense"))
        sedentary_goals = set(nutrition.goals_for("sedentaire"))
        self.assertFalse(athlete_goals & sedentary_goals)
        self.assertIn("seche", athlete_goals)
        self.assertIn("maintien", sedentary_goals)

    def test_cut_versus_bulk(self):
        cut = nutrition.daily_targets(ATHLETE.with_(goal="seche"))
        bulk = nutrition.daily_targets(ATHLETE.with_(goal="prise_de_masse"))
        self.assertLess(cut.kcal, bulk.kcal)
        self.assertGreater(cut.protein, bulk.protein)  # 2,4 vs 2,0 g/kg

    def test_macros_match_energy(self):
        for profile in (ATHLETE, SEDENTARY, ATHLETE.with_(goal="seche")):
            targets = nutrition.daily_targets(profile)
            energy = targets.protein * 4 + targets.carbs * 4 + targets.fat * 9
            self.assertAlmostEqual(energy, targets.kcal, places=4)

    def test_fat_floor_is_respected(self):
        lean = Profile(weight_kg=95, height_cm=170, age=45, sex="femme",
                       activity="modere", goal="seche")
        targets = nutrition.daily_targets(lean)
        self.assertGreaterEqual(targets.fat, 0.8 * lean.weight_kg * 0.74)

    def test_meal_split_sums_to_daily_targets(self):
        for meals_per_day in (3, 4, 5):
            targets = nutrition.daily_targets(ATHLETE.with_(meals_per_day=meals_per_day))
            slots = nutrition.split_by_meal(targets, meals_per_day)
            self.assertEqual(len(slots), meals_per_day)
            for macro in ("protein", "carbs", "fat"):
                total = sum(getattr(slot, macro) for slot in slots)
                self.assertAlmostEqual(total, getattr(targets, macro), places=6)
            self.assertAlmostEqual(
                sum(slot.kcal for slot in slots), targets.kcal, places=4
            )

    def test_carbs_are_front_loaded(self):
        targets = nutrition.daily_targets(ATHLETE)
        slots = {s.key: s for s in nutrition.split_by_meal(targets, 4)}
        # À énergie comparable, le dîner est moins glucidique que le déjeuner.
        self.assertLess(
            slots["diner"].carbs / slots["diner"].kcal,
            slots["dejeuner"].carbs / slots["dejeuner"].kcal,
        )


class TestFoodsAndRecipes(unittest.TestCase):
    def test_food_ids_are_unique_and_consistent(self):
        for food_id, food in FOODS.items():
            self.assertEqual(food_id, food.id)
            energy = food.per100g.protein * 4 + food.per100g.carbs * 4 + food.per100g.fat * 9
            # Tolérance large : fibres, alcool, polyols et arrondis des tables.
            self.assertLess(
                abs(energy - food.per100g.kcal), max(45.0, food.per100g.kcal * 0.25),
                msg=f"Incohérence énergétique pour {food_id}",
            )

    def test_recipe_count_and_ingredients(self):
        self.assertGreaterEqual(len(RECIPES), 8)
        self.assertLessEqual(len(RECIPES), 10)
        for recipe in RECIPES:
            self.assertTrue(recipe.meals)
            self.assertTrue(recipe.steps)
            for ingredient in recipe.ingredients:
                self.assertIn(ingredient.food_id, FOODS)

    def test_recipe_facts_scale_linearly(self):
        recipe = RECIPES_BY_ID["riz_poulet_brocolis"]
        single = recipe_facts(recipe, 1.0)
        double = recipe_facts(recipe, 2.0)
        self.assertAlmostEqual(double.kcal, single.kcal * 2, places=6)
        self.assertGreater(single.protein, 40)  # plat très protéiné

    def test_recipes_cover_every_meal_slot(self):
        for meals_per_day in (3, 4, 5):
            for slot in nutrition.MEAL_PLANS[meals_per_day]:
                self.assertTrue(
                    [r for r in RECIPES if slot.key in r.meals]
                    or slot.key.startswith("collation"),
                    msg=f"Aucune recette pour {slot.key}",
                )


class TestPantry(unittest.TestCase):
    def _items(self):
        return [
            PantryItem(id=1, food_id="poulet_blanc", grams=200,
                       expiry=TODAY + timedelta(days=1)),
            PantryItem(id=2, food_id="poulet_blanc", grams=300,
                       expiry=TODAY + timedelta(days=9)),
            PantryItem(id=3, food_id="riz_blanc", grams=1000, expiry=None),
            PantryItem(id=4, food_id="brocoli", grams=150,
                       expiry=TODAY - timedelta(days=2)),
        ]

    def test_expired_lots_are_excluded_by_default(self):
        lots = pantry.build_lots(self._items(), TODAY)
        self.assertNotIn("brocoli", {lot.food_id for lot in lots})
        self.assertIn("brocoli", {
            lot.food_id for lot in pantry.build_lots(self._items(), TODAY, include_expired=True)
        })

    def test_urgency_is_monotonic(self):
        self.assertEqual(pantry.urgency_score(0), 1.0)
        self.assertEqual(pantry.urgency_score(None), 0.0)
        self.assertEqual(pantry.urgency_score(30), 0.0)
        self.assertGreater(pantry.urgency_score(1), pantry.urgency_score(5))

    def test_draw_consumes_soonest_expiry_first(self):
        lots = pantry.build_lots(self._items(), TODAY)
        result = pantry.draw(lots, "poulet_blanc", 250)
        self.assertAlmostEqual(result.taken, 250)
        self.assertEqual(result.missing, 0)
        self.assertEqual(result.soonest_days_left, 1)
        # 200 g urgents + 50 g non urgents : urgence moyenne élevée mais < 1.
        self.assertGreater(result.urgency, 0.5)
        self.assertLess(result.urgency, 1.0)

    def test_draw_reports_missing_quantity(self):
        lots = pantry.build_lots(self._items(), TODAY)
        result = pantry.draw(lots, "saumon", 150)
        self.assertEqual(result.taken, 0)
        self.assertAlmostEqual(result.missing, 150)
        self.assertFalse(result.covered)


class TestSuggester(unittest.TestCase):
    def setUp(self):
        self.targets = nutrition.daily_targets(ATHLETE)
        self.meals = {m.key: m for m in nutrition.split_by_meal(self.targets, 4)}

    def test_expiring_ingredient_is_prioritised(self):
        """Deux plats équivalents : celui qui sauve un aliment gagne."""
        base = [
            PantryItem(food_id="poulet_blanc", grams=600),
            PantryItem(food_id="riz_blanc", grams=1000),
            PantryItem(food_id="brocoli", grams=600),
            PantryItem(food_id="huile_olive", grams=500),
            PantryItem(food_id="oignon", grams=300),
            PantryItem(food_id="thon_naturel", grams=400),
            PantryItem(food_id="quinoa", grams=500),
            PantryItem(food_id="haricots_verts", grams=600),
            PantryItem(food_id="tomate", grams=300),
        ]
        target = self.meals["dejeuner"].as_facts()
        candidates = [RECIPES_BY_ID["riz_poulet_brocolis"],
                      RECIPES_BY_ID["thon_quinoa_haricots"]]

        neutral = suggester.suggest(
            target, pantry.build_lots(base, TODAY), "dejeuner",
            limit=2, candidates=candidates,
        )
        # Le thon devient urgent : il doit remonter en tête.
        urgent_items = [
            PantryItem(food_id=i.food_id, grams=i.grams,
                       expiry=TODAY if i.food_id == "thon_naturel" else None)
            for i in base
        ]
        urgent = suggester.suggest(
            target, pantry.build_lots(urgent_items, TODAY), "dejeuner",
            limit=2, candidates=candidates,
        )
        self.assertEqual(urgent[0].recipe.id, "thon_quinoa_haricots")
        self.assertGreater(
            urgent[0].score,
            next(s.score for s in neutral if s.recipe.id == "thon_quinoa_haricots"),
        )

    def test_missing_ingredient_gets_a_substitution(self):
        items = [
            PantryItem(food_id="poulet_blanc", grams=400),
            PantryItem(food_id="riz_complet", grams=800),  # à la place du riz blanc
            PantryItem(food_id="brocoli", grams=400),
            PantryItem(food_id="huile_olive", grams=300),
        ]
        result = suggester.suggest(
            self.meals["dejeuner"].as_facts(), pantry.build_lots(items, TODAY),
            "dejeuner", limit=1, candidates=[RECIPES_BY_ID["riz_poulet_brocolis"]],
        )[0]
        missing = {ing.food.id: ing for ing in result.missing}
        self.assertIn("riz_blanc", missing)
        substitution = missing["riz_blanc"].substitution
        self.assertIsNotNone(substitution)
        self.assertEqual(substitution.replacement.id, "riz_complet")
        self.assertTrue(substitution.in_pantry)

    def test_only_cookable_filters_out_incomplete_recipes(self):
        items = [PantryItem(food_id="poulet_blanc", grams=400)]
        lots = pantry.build_lots(items, TODAY)
        target = self.meals["dejeuner"].as_facts()
        self.assertTrue(suggester.suggest(target, lots, "dejeuner", limit=5))
        self.assertFalse(
            suggester.suggest(target, lots, "dejeuner", limit=5, only_cookable=True)
        )

    def test_portion_scaling_improves_fit(self):
        items = [
            PantryItem(food_id=ing.food_id, grams=5000)
            for ing in RECIPES_BY_ID["riz_poulet_brocolis"].ingredients
        ]
        lots = pantry.build_lots(items, TODAY)
        target = self.meals["dejeuner"].as_facts()
        result = suggester.suggest(
            target, lots, "dejeuner", limit=1,
            candidates=[RECIPES_BY_ID["riz_poulet_brocolis"]],
        )[0]
        base_fit = suggester.macro_fit(
            recipe_facts(RECIPES_BY_ID["riz_poulet_brocolis"], 1.0), target
        )
        self.assertGreaterEqual(result.fit, base_fit)
        self.assertTrue(result.cookable_now)

    def test_plan_day_avoids_repeating_recipes(self):
        items = [PantryItem(food_id=fid, grams=3000) for fid in FOODS]
        lots = pantry.build_lots(items, TODAY)
        meals = nutrition.split_by_meal(self.targets, 4)
        plan = suggester.plan_day(meals, lots)
        chosen = [s.recipe.id for s in plan.values() if s]
        self.assertEqual(len(chosen), len(set(chosen)))

    def test_macro_fit_is_bounded(self):
        target = NutritionFacts(kcal=800, protein=50, carbs=80, fat=25)
        self.assertAlmostEqual(suggester.macro_fit(target, target), 1.0)
        self.assertGreaterEqual(
            suggester.macro_fit(NutritionFacts(kcal=1, protein=1, carbs=1, fat=1), target),
            0.0,
        )


class TestSubstitutions(unittest.TestCase):
    def test_prefers_pantry_over_shopping(self):
        result = substitutions.suggest_substitute(
            "poulet_blanc", 150, {"dinde_escalope": 500}
        )
        self.assertEqual(result.replacement.id, "dinde_escalope")
        self.assertTrue(result.in_pantry)

    def test_falls_back_to_a_food_to_buy(self):
        result = substitutions.suggest_substitute("saumon", 150, {})
        self.assertIsNotNone(result)
        self.assertFalse(result.in_pantry)

    def test_quantity_is_anchored_on_dominant_nutrient(self):
        # 150 g de poulet (31 g P/100 g) ≈ 160 g de dinde (29 g P/100 g).
        result = substitutions.suggest_substitute(
            "poulet_blanc", 150, {"dinde_escalope": 500}
        )
        expected = 150 * 31.0 / 29.0
        self.assertLess(abs(result.grams - expected), 6)

    def test_absurd_conversions_are_rejected(self):
        # Remplacer de l'huile par de la salade demanderait un facteur délirant.
        result = substitutions.suggest_substitute(
            "huile_olive", 10, {"salade_verte": 500}
        )
        self.assertNotEqual(getattr(result, "replacement", None), get_food("salade_verte"))

    def test_unknown_food_returns_none(self):
        self.assertIsNone(substitutions.suggest_substitute("licorne", 100, {}))


class TestAnalytics(unittest.TestCase):
    def setUp(self):
        self.targets = nutrition.daily_targets(ATHLETE)

    def _logs(self, days: int, scale: float, recipe_id="riz_poulet_brocolis"):
        recipe = RECIPES_BY_ID[recipe_id]
        return [
            MealLog(day=TODAY - timedelta(days=offset), meal="dejeuner",
                    label=recipe.name, recipe_id=recipe.id,
                    facts=recipe_facts(recipe, scale))
            for offset in range(days)
        ]

    def test_not_enough_data_yields_no_diagnosis(self):
        report = analytics.analyse_window(self._logs(2, 1.0), self.targets, TODAY)
        self.assertFalse(report.has_enough_data)
        self.assertEqual(report.alerts, [])

    def test_recurrent_deficit_is_detected(self):
        report = analytics.analyse_window(self._logs(7, 1.0), self.targets, TODAY)
        self.assertTrue(report.has_enough_data)
        keys = {alert.key for alert in report.alerts}
        self.assertIn("kcal", keys)
        self.assertIn("fiber", keys)
        deficit = next(a for a in report.alerts if a.key == "fiber")
        self.assertEqual(deficit.kind, "deficit")
        self.assertEqual(deficit.logged_days, 7)
        self.assertTrue(deficit.foods)

    def test_one_off_day_is_not_flagged(self):
        """Six journées correctes et une journée basse ne déclenchent rien."""
        logs = []
        for offset in range(7):
            scale = 0.2 if offset == 3 else 1.0
            logs.append(
                MealLog(day=TODAY - timedelta(days=offset), meal="dejeuner",
                        label="repas complet", recipe_id=None,
                        facts=self.targets.as_facts() * scale)
            )
        report = analytics.analyse_window(logs, self.targets, TODAY)
        deficits = [a for a in report.alerts if a.kind == "deficit"]
        self.assertEqual(deficits, [])

    def test_excess_is_detected(self):
        logs = [
            MealLog(day=TODAY - timedelta(days=offset), meal="dejeuner",
                    label="excès", recipe_id=None,
                    facts=self.targets.as_facts() * 1.6)
            for offset in range(6)
        ]
        report = analytics.analyse_window(logs, self.targets, TODAY)
        self.assertIn("exces", {alert.kind for alert in report.alerts})

    def test_monotony_alert(self):
        report = analytics.analyse_window(self._logs(7, 1.0), self.targets, TODAY)
        self.assertIn("monotonie", {alert.kind for alert in report.alerts})

    def test_incomplete_current_day_is_excluded(self):
        """Un seul repas logué aujourd'hui ne doit pas créer de faux déficit."""
        logs = []
        for offset in range(1, 6):
            for meal in ("petit_dej", "dejeuner", "diner"):
                logs.append(
                    MealLog(day=TODAY - timedelta(days=offset), meal=meal,
                            label="repas", recipe_id=None,
                            facts=self.targets.as_facts() * (1 / 3))
                )
        logs.append(
            MealLog(day=TODAY, meal="petit_dej", label="petit-déj",
                    recipe_id=None, facts=self.targets.as_facts() * (1 / 3))
        )
        report = analytics.analyse_window(logs, self.targets, TODAY)
        self.assertTrue(report.day_in_progress)
        self.assertEqual(report.logged_days, 5)
        self.assertEqual(len(report.days), 6)  # le graphique garde tout
        self.assertEqual([a for a in report.alerts if a.kind == "deficit"], [])

    def test_complete_current_day_is_kept(self):
        logs = []
        for offset in range(0, 5):
            for meal in ("petit_dej", "dejeuner", "diner"):
                logs.append(
                    MealLog(day=TODAY - timedelta(days=offset), meal=meal,
                            label="repas", recipe_id=None,
                            facts=self.targets.as_facts() * (1 / 3))
                )
        report = analytics.analyse_window(logs, self.targets, TODAY)
        self.assertFalse(report.day_in_progress)
        self.assertEqual(report.logged_days, 5)

    def test_window_ignores_older_days(self):
        logs = self._logs(3, 1.0) + [
            MealLog(day=TODAY - timedelta(days=20), meal="diner", label="vieux",
                    facts=NutritionFacts(kcal=5000))
        ]
        report = analytics.analyse_window(logs, self.targets, TODAY)
        self.assertEqual(report.logged_days, 3)


class TestStorage(unittest.TestCase):
    def setUp(self):
        self.store = Store(":memory:")

    def test_profile_roundtrip(self):
        self.assertIsNone(self.store.load_profile())
        self.store.save_profile(ATHLETE)
        self.assertEqual(self.store.load_profile(), ATHLETE)
        self.store.save_profile(SEDENTARY)  # écrase, ne duplique pas
        self.assertEqual(self.store.load_profile(), SEDENTARY)

    def test_pantry_merges_identical_lots(self):
        self.store.add_pantry_item("riz_blanc", 500, None)
        self.store.add_pantry_item("riz_blanc", 300, None)
        items = self.store.list_pantry()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].grams, 800)

    def test_pantry_keeps_distinct_expiry_dates(self):
        self.store.add_pantry_item("poulet_blanc", 200, TODAY + timedelta(days=1))
        self.store.add_pantry_item("poulet_blanc", 300, TODAY + timedelta(days=8))
        self.assertEqual(len(self.store.list_pantry()), 2)

    def test_consume_applies_fefo(self):
        self.store.add_pantry_item("poulet_blanc", 200, TODAY + timedelta(days=1))
        self.store.add_pantry_item("poulet_blanc", 300, TODAY + timedelta(days=8))
        self.store.consume([("poulet_blanc", 250)])
        remaining = self.store.list_pantry()
        self.assertEqual(len(remaining), 1)
        self.assertAlmostEqual(remaining[0].grams, 250)
        self.assertEqual(remaining[0].expiry, TODAY + timedelta(days=8))

    def test_purge_expired(self):
        self.store.add_pantry_item("brocoli", 200, TODAY - timedelta(days=1))
        self.store.add_pantry_item("riz_blanc", 500, None)
        self.assertEqual(self.store.purge_expired(TODAY), 1)
        self.assertEqual(len(self.store.list_pantry()), 1)

    def test_log_roundtrip_and_filtering(self):
        recipe = RECIPES_BY_ID["oeufs_avoine"]
        facts = recipe_facts(recipe, 1.5)
        log_id = self.store.add_log(
            MealLog(day=TODAY, meal="petit_dej", label=recipe.name,
                    facts=facts, recipe_id=recipe.id, portions=1.5)
        )
        self.store.add_log(
            MealLog(day=TODAY - timedelta(days=30), meal="diner", label="vieux",
                    facts=NutritionFacts(kcal=700))
        )
        recent = self.store.list_logs(start=TODAY - timedelta(days=6), end=TODAY)
        self.assertEqual(len(recent), 1)
        self.assertAlmostEqual(recent[0].facts.kcal, facts.kcal, places=4)
        self.assertEqual(recent[0].portions, 1.5)
        self.assertEqual(
            self.store.recent_recipe_ids(TODAY - timedelta(days=2)), [recipe.id]
        )
        self.store.delete_log(log_id)
        self.assertEqual(len(self.store.list_logs(start=TODAY, end=TODAY)), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
