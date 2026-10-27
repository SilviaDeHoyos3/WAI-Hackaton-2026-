import math
from pathlib import Path
import unittest

from freshwise.demo import FIXTURES, baseline_plan
try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    AppTest = None


class PlanTests(unittest.TestCase):
    def test_known_cases_and_stock_above_forecast(self):
        plan = baseline_plan(FIXTURES["Demo meal A"], 20, 1, 3)
        self.assertEqual(plan["preparation"], 80)
        self.assertEqual([r["Simulated excess (portions)"] for r in plan["scenarios"]], [30, 0, 0])
        self.assertEqual([r["Simulated unmet orders"] for r in plan["scenarios"]], [0, 0, 30])
        self.assertEqual(plan["scenarios"][2]["Penalty loss (cost units)"], 90)
        self.assertEqual(baseline_plan(FIXTURES["Demo meal A"], 120, 1, 3)["preparation"], 0)

    def test_invalid_inputs(self):
        for bad in (None, "", -1, math.nan, math.inf, True):
            for index in range(3):
                args = [20, 1, 3]
                args[index] = bad
                with self.subTest(value=bad, field=index), self.assertRaises(ValueError):
                    baseline_plan(FIXTURES["Demo meal A"], *args)


@unittest.skipIf(AppTest is None, "Install the demo extra to run screen tests")
class ScreenTests(unittest.TestCase):
    def test_selection_changes_and_validation_clear_results(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[2].value, "80")
        app.number_input(key="stock_DEMO_MEAL_A").set_value(120).run()
        self.assertEqual(app.metric[2].value, "0")
        app.selectbox(key="meal").select("Demo meal B").run()
        self.assertEqual(app.metric[1].value, "160")
        self.assertEqual(app.metric[2].value, "140")
        app.number_input(key="underage").set_value(5.0).run()
        self.assertEqual(app.dataframe[0].value.iloc[2]["Penalty loss (cost units)"], 240)
        app.number_input(key="stock_DEMO_MEAL_B").set_value(-1).run()
        self.assertTrue(app.error)
        self.assertEqual(len(app.metric), 2)
        self.assertEqual(len(app.dataframe), 0)
        self.assertFalse(app.exception)

    def test_blank_input_clears_plan(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run()
        app.number_input(key="stock_DEMO_MEAL_A").set_value(None).run()
        self.assertTrue(app.error)
        self.assertEqual(len(app.dataframe), 0)
        self.assertFalse(app.exception)
