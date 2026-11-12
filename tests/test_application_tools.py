import unittest
from freshwise.application_tools import invoke, reject_guarantee


class ApplicationToolTests(unittest.TestCase):
    def test_only_manager_inputs_cross_public_boundary(self):
        for field, value in (("forecast", 9999), ("error_ratios", [99]), ("quantile", 1)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                invoke("central_preparation_recommendation", {"usable_stock": 20, field: value})

    def test_missing_values_do_not_call_tools(self):
        result = invoke("manager_adjusted_central_recommendation", {"usable_stock": 20})
        self.assertEqual(result["status"], "needs_input")
        self.assertEqual(result["missing"], ["manager_estimate", "opinion_weight"])
        self.assertIsNone(result["tool_call"])

    def test_missing_context_does_not_fall_back(self):
        with self.assertRaises(ValueError):
            invoke("central_preparation_recommendation", {"usable_stock": 20}, "unknown-real-meal")

    def test_invalid_values_and_unknown_tools(self):
        for value in (-1, float("nan"), float("inf"), True, 1.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                invoke("central_preparation_recommendation", {"usable_stock": value})
        with self.assertRaises(ValueError):
            invoke("place_real_order", {"usable_stock": 20})

    def test_missing_stock_is_requested(self):
        self.assertEqual(invoke("central_preparation_recommendation", {})["missing"], ["usable_stock"])

    def test_tool_failure_propagates(self):
        from unittest.mock import patch
        with patch("freshwise.application_tools.central_preparation_recommendation", side_effect=ValueError("calibration unavailable")):
            with self.assertRaisesRegex(ValueError, "calibration unavailable"):
                invoke("central_preparation_recommendation", {"usable_stock": 20})

    def test_guarantee_has_no_fabricated_plan(self):
        response = reject_guarantee()
        self.assertEqual(response["status"], "cannot_guarantee")
        self.assertIsNone(response["result"])


class RealContextTests(unittest.TestCase):
    def test_unrounded_tool_forecast_reaches_decision(self):
        from unittest.mock import patch
        from freshwise.application_tools import context_for_meal
        record = {"forecast_orders":100.01,"forecast_orders_display":100.0,
                  "history_end_week":145,"target_week":146,"provenance":"hgb exact output"}
        with patch("freshwise.application_tools.forecast_tool", return_value=record):
            context = context_for_meal(13,1198,object())
        response = invoke("central_preparation_recommendation", {"usable_stock":20}, context=context)
        self.assertEqual(response["result"]["new_portions_to_prepare"],81)
        self.assertEqual(response["tool_call"]["application_arguments"],{"forecast":100.01})
        self.assertEqual(response["forecast_record"],record)
        with self.assertRaisesRegex(ValueError,"matching calibration"):
            invoke("preparation_recommendation",{"usable_stock":20},context=context)

    def test_forecast_error_is_not_replaced_by_fixture(self):
        from unittest.mock import patch
        from freshwise.application_tools import context_for_meal
        with patch("freshwise.application_tools.forecast_tool",return_value={"error":"unknown meal"}):
            with self.assertRaisesRegex(ValueError,"unknown meal"):
                context_for_meal(13,9999,object())

    def test_fewer_shortages_fixture_uses_configured_quantile(self):
        response = invoke("preparation_recommendation",{"usable_stock":20})
        self.assertEqual(response["result"]["new_portions_to_prepare"],100)
        self.assertEqual(response["tool_call"]["application_arguments"]["quantile"],5/7)
        self.assertIn("waste",response["answer"])
