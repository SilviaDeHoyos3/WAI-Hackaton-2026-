"""Synthetic UI fixture and forecast-matching baseline, pending team integration."""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class DemoForecast:
    center_id: str
    meal_id: str
    target_week: int
    forecast_orders: float
    method: str = "Synthetic fixture (not a trained model)"


FIXTURES = {
    "Demo meal A": DemoForecast("DEMO_CENTER", "DEMO_MEAL_A", 146, 100),
    "Demo meal B": DemoForecast("DEMO_CENTER", "DEMO_MEAL_B", 146, 160),
    "Demo meal C": DemoForecast("DEMO_CENTER", "DEMO_MEAL_C", 146, 60),
}


def nonnegative(value, name):
    """Reject absent, nonnumeric and non-finite values before calculating."""
    if value is None or isinstance(value, bool):
        raise ValueError(f"{name} is required and must be a finite non-negative number.")
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError):
        raise ValueError(f"{name} must be a finite non-negative number.") from None
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{name} must be a finite non-negative number.")
    return number


def baseline_plan(forecast, inventory, overage, underage):
    """Simple fixture baseline, not Ari's optimized recommendation function.

    Assumes one order per portion, no carry-over, no lead time or capacity limit.
    Scenario demand is rounded up to whole orders. Penalties affect scenario loss,
    not the preparation quantity of this forecast-matching baseline.
    """
    orders = nonnegative(forecast.forecast_orders, "Forecast")
    stock = nonnegative(inventory, "Usable stock")
    excess_penalty = nonnegative(overage, "Excess penalty")
    shortage_penalty = nonnegative(underage, "Shortage penalty")
    if stock != int(stock):
        raise ValueError("Usable stock must be a whole number of portions.")
    preparation = max(0, math.ceil(orders - stock))
    supply = stock + preparation
    rows = []
    for label, multiplier in (("Low", 0.7), ("Base", 1.0), ("High", 1.3)):
        demand = math.ceil(orders * multiplier)
        excess = max(0, supply - demand)
        unmet = max(0, demand - supply)
        loss = excess * excess_penalty + unmet * shortage_penalty
        if not math.isfinite(loss):
            raise ValueError("Penalty loss is too large; use smaller penalties.")
        rows.append({"Scenario": label, "Assumed orders": demand,
                     "Total supply (portions)": int(supply),
                     "Simulated excess (portions)": int(excess),
                     "Simulated unmet orders": int(unmet),
                     "Penalty loss (cost units)": loss})
    return {"preparation": preparation, "supply": int(supply), "scenarios": rows,
            "policy": "Forecast-matching baseline", "assumption_version": "demo-v1"}
