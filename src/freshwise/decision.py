import math
from numbers import Real, Integral

def _validate_nonnegative_number(value, name):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a number.")

    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite.")

    if value < 0:
        raise ValueError(f"{name} cannot be negative.")

def recommend_preparation(forecast, inventory):
    _validate_nonnegative_number(forecast, "Forecast")
    _validate_inventory(inventory)

    return max(0, math.ceil(forecast - inventory))

def evaluate_preparation(prepared, inventory, actual_orders):
    _validate_nonnegative_number(prepared, "Prepared quantity")
    _validate_inventory(inventory)
    _validate_nonnegative_number(actual_orders, "Actual orders")

    supply = inventory + prepared

    excess = max(0, supply - actual_orders)
    unmet = max(0, actual_orders - supply)

    return {"excess": excess, "unmet": unmet}

def calculate_loss(excess, unmet, overage_cost, underage_cost):
    _validate_nonnegative_number(excess, "Excess")
    _validate_nonnegative_number(unmet, "Unmet orders")
    _validate_nonnegative_number(overage_cost, "Overage cost")
    _validate_nonnegative_number(underage_cost, "Underage cost")

    return excess * overage_cost + unmet * underage_cost

def average_scenario_loss(
    prepared,
    inventory,
    demand_scenarios,
    overage_cost,
    underage_cost,
):
    if not demand_scenarios:
        raise ValueError("Provide at least one demand scenario.")

    losses = []

    for demand in demand_scenarios:
        result = evaluate_preparation(prepared, inventory, demand)

        loss = calculate_loss(
            result["excess"],
            result["unmet"],
            overage_cost,
            underage_cost,
        )

        losses.append(loss)

    return sum(losses) / len(losses)

def optimize_preparation(
    inventory,
    demand_scenarios,
    overage_cost,
    underage_cost,
):
    if not demand_scenarios:
        raise ValueError("Provide at least one demand scenario.")

    _validate_inventory(inventory)
    _validate_nonnegative_number(overage_cost, "Overage cost")
    _validate_nonnegative_number(underage_cost, "Underage cost")

    for demand in demand_scenarios:
        _validate_nonnegative_number(demand, "Demand scenario")

    max_preparation = max(
        0,
        math.ceil(max(demand_scenarios) - inventory),
    )

    best_preparation = 0
    best_loss = float("inf")

    for prepared in range(max_preparation + 1):
        loss = average_scenario_loss(
            prepared,
            inventory,
            demand_scenarios,
            overage_cost,
            underage_cost,
        )

        if loss < best_loss:
            best_preparation = prepared
            best_loss = loss

    return {
        "prepare_qty": best_preparation,
        "average_loss": best_loss,
    }


def adjust_demand_scenarios(
    demand_scenarios,
    anchor_index,
    manager_estimate,
    opinion_weight,
):
    if not demand_scenarios:
        raise ValueError("Provide at least one demand scenario.")

    for demand in demand_scenarios:
        _validate_nonnegative_number(demand, "Demand scenario")

    if isinstance(anchor_index, bool) or not isinstance(
        anchor_index, Integral
    ):
        raise ValueError("Anchor index must be an integer.")
    
    if not 0 <= anchor_index < len(demand_scenarios):
        raise ValueError("Anchor index is out of range.")

    _validate_nonnegative_number(manager_estimate, "Manager estimate")
    _validate_nonnegative_number(opinion_weight, "Opinion weight")

    if opinion_weight > 1:
        raise ValueError("Opinion weight must be between 0 and 1.")
    
    anchor = demand_scenarios[anchor_index]

    custom_anchor = (
        (1 - opinion_weight) * anchor
        + opinion_weight * manager_estimate
    )

    adjustment = custom_anchor - anchor

    updated_scenarios = [
        max(0, demand + adjustment)
        for demand in demand_scenarios
    ]

    return {
        "original_scenarios": list(demand_scenarios),
        "anchor": anchor,
        "manager_estimate": manager_estimate,
        "opinion_weight": opinion_weight,
        "custom_anchor": custom_anchor,
        "adjustment": adjustment,
        "updated_scenarios": updated_scenarios,
        "clipped": any(
            demand + adjustment < 0
            for demand in demand_scenarios
        ),
    }

def compare_preparation_plans(
    inventory,
    demand_scenarios,
    overage_cost,
    underage_cost,
    anchor_index,
    manager_estimate,
    opinion_weight,
):
    original_scenarios = list(demand_scenarios)

    if len(original_scenarios) != 3:
        raise ValueError("Provide exactly three demand scenarios.")

    for demand in original_scenarios:
        _validate_nonnegative_number(demand, "Demand scenario")

    low, central, high = original_scenarios

    if not low <= central <= high:
        raise ValueError(
            "Demand scenarios must satisfy low <= central <= high."
        )

    custom = adjust_demand_scenarios(
        original_scenarios,
        anchor_index,
        manager_estimate,
        opinion_weight,
    )

    updated_scenarios = custom["updated_scenarios"]

    original_plan = optimize_preparation(
        inventory,
        original_scenarios,
        overage_cost,
        underage_cost,
    )

    custom_plan = optimize_preparation(
        inventory,
        updated_scenarios,
        overage_cost,
        underage_cost,
    )

    original_on_updated = average_scenario_loss(
        original_plan["prepare_qty"],
        inventory,
        updated_scenarios,
        overage_cost,
        underage_cost,
    )

    custom_on_original = average_scenario_loss(
        custom_plan["prepare_qty"],
        inventory,
        original_scenarios,
        overage_cost,
        underage_cost,
    )

    return {
        "inputs": {
            "inventory": inventory,
            "overage_cost": overage_cost,
            "underage_cost": underage_cost,
            "anchor_index": anchor_index,
            "manager_estimate": manager_estimate,
            "opinion_weight": opinion_weight,
        },
        "original_scenarios": original_scenarios,
        "custom_adjustment": custom,
        "original_plan": original_plan,
        "custom_plan": custom_plan,
        "loss_comparison": {
            "original_plan": {
                "on_original": original_plan["average_loss"],
                "on_updated": original_on_updated,
            },
            "custom_plan": {
                "on_original": custom_on_original,
                "on_updated": custom_plan["average_loss"],
            },
        },
    }

def _validate_inventory(inventory):
    _validate_nonnegative_number(inventory, "Inventory")

    if inventory % 1 != 0:
        raise ValueError("Inventory must contain whole portions.")
