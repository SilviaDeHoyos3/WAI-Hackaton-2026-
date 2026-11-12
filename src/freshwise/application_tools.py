"""Application-owned forecast context and validated calls to teammate tools.

No language model is connected. Public arguments contain manager inputs only.
"""
from dataclasses import dataclass
from numbers import Real
from pathlib import Path
import math
import os
import pandas as pd
from .agent_tools import (central_preparation_recommendation,
    manager_adjusted_central_recommendation, preparation_recommendation)
from .agent_data_tools import context_from_tables, forecast_tool

@dataclass(frozen=True)
class PlanningContext:
    key: str
    forecast: float
    source: str
    forecast_record: dict | None = None
    error_ratios: tuple[float, ...] | None = None
    quantile: float | None = None

CONTEXTS = {"acceptance-fixture": PlanningContext(
    "acceptance-fixture", 100, "Synthetic acceptance fixture; not project calibration",
    error_ratios=(0.8, 1.0, 1.2), quantile=5/7)}

def get_context(key):
    if key not in CONTEXTS:
        raise ValueError("No verified planning context is available.")
    return CONTEXTS[key]

DATA_FILES = ("train.csv", "test.csv", "meal_info.csv", "fulfilment_center_info.csv")

def resolve_data_dir(path=None):
    # This UI needs four demand files, not the unrelated emissions datasets.
    if path or os.environ.get("FRESHWISE_DATA_DIR"):
        candidates = [Path(path or os.environ["FRESHWISE_DATA_DIR"]).expanduser()]
    else:
        root = Path(__file__).resolve().parents[2]
        candidates = [root / "data", root / "Data", root.parent / "Data"]
    for candidate in candidates:
        if all((candidate / name).is_file() for name in DATA_FILES):
            return candidate.resolve()
    raise FileNotFoundError("Set FRESHWISE_DATA_DIR to a folder containing " + ", ".join(DATA_FILES))

def load_application_data(path=None):
    root = resolve_data_dir(path)
    tables = [pd.read_csv(root / name) for name in DATA_FILES]
    return context_from_tables(*tables)

def context_for_meal(center_id, meal_id, data_context):
    record = forecast_tool(center_id, meal_id, data_context, method="hgb")
    if "error" in record:
        raise ValueError(record["error"])
    forecast = _number(record["forecast_orders"], "Forecast")
    if record["history_end_week"] >= record["target_week"]:
        raise ValueError("Forecast history must end before the target week.")
    return PlanningContext(
        f"center-{center_id}/meal-{meal_id}/week-{record['target_week']}",
        forecast, record["provenance"], forecast_record=record)

def _number(value, label, whole=False, upper=None):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{label} must be a number.")
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{label} must be finite and non-negative.")
    if whole and value % 1:
        raise ValueError(f"{label} must contain whole portions.")
    if upper is not None and value > upper:
        raise ValueError(f"{label} must be between 0 and {upper}.")
    return int(value) if whole else float(value)

def invoke(tool_name, arguments, context_key="acceptance-fixture", *, context=None):
    """A future AI dispatcher may pass manager arguments, never forecast/ratios.

    The context keyword is supplied by application code, not an AI tool schema.
    Real fewer-shortages mode stays unavailable until matching calibration is supplied.
    """
    if not isinstance(arguments, dict):
        raise ValueError("Tool arguments must be an object.")
    required = {"usable_stock"}
    if tool_name == "manager_adjusted_central_recommendation":
        required |= {"manager_estimate", "opinion_weight"}
    elif tool_name not in ("central_preparation_recommendation", "preparation_recommendation"):
        raise ValueError("Unknown planning tool.")
    if set(arguments) - required:
        raise ValueError("Unexpected arguments: forecast, calibration and quantile are application-owned.")
    missing = sorted(k for k in required if arguments.get(k) is None or arguments.get(k) == "")
    if missing:
        return {"status": "needs_input", "missing": missing, "tool_call": None,
                "result": None, "answer": "Please provide: " + ", ".join(missing) + "."}
    context = context if context is not None else get_context(context_key)
    values = {"forecast": _number(context.forecast, "Forecast"),
              "usable_stock": _number(arguments["usable_stock"], "Usable stock", whole=True)}
    application_args = {"forecast": values["forecast"]}
    if tool_name == "manager_adjusted_central_recommendation":
        values.update(manager_estimate=_number(arguments["manager_estimate"], "Manager estimate"),
                      opinion_weight=_number(arguments["opinion_weight"], "Opinion weight", upper=1))
        result = manager_adjusted_central_recommendation(**values)
        original, adjusted, manager = result["original_plan"], result["adjusted_plan"], result["manager_context"]
        answer = (f"Original forecast: {original['forecast_orders']:g} orders. "
                  f"Manager estimate: {manager['manager_estimate']:g}; weight: {manager['opinion_weight']:.0%}. "
                  f"Target change: {manager['demand_shift']:+g} orders. "
                  f"Original preparation: {original['new_portions_to_prepare']} portions; "
                  f"adjusted preparation: {adjusted['new_portions_to_prepare']} portions. "
                  "Manager adjustments were not part of the evaluated policy results.")
    else:
        if tool_name == "preparation_recommendation":
            if context.error_ratios is None or context.quantile != 5/7:
                raise ValueError("Fewer-shortages mode needs matching calibration ratios and configured quantile 5/7; no substitute is used.")
            values.update(error_ratios=list(context.error_ratios), quantile=context.quantile)
            application_args.update(error_ratios=values["error_ratios"], quantile=context.quantile)
            result = preparation_recommendation(**values)
        else:
            result = central_preparation_recommendation(**values)
        answer = (f"Prepare {result['new_portions_to_prepare']} new portions. "
                  f"Usable stock: {result['usable_stock']}; total available: {result['total_available']} portions. "
                  f"Policy target: {result['target_supply']:g}, not guaranteed demand.")
        if tool_name == "preparation_recommendation":
            answer += " Fewer-shortages policy (q=5/7) may increase excess preparation and waste."
    return {"status": "success", "missing": [], "context_key": context.key,
            "context_source": context.source, "forecast_record": context.forecast_record,
            "tool_call": {"name": tool_name, "manager_arguments": arguments,
                          "application_arguments": application_args},
            "result": result, "answer": answer}

def reject_guarantee():
    return {"status": "cannot_guarantee", "tool_call": None, "result": None,
            "answer": "Uncertain demand prevents a guarantee of both zero waste and zero unmet orders. "
                      "I can calculate a plan using explicit stock and policy assumptions instead."}
