import math


def recommend_preparation(forecast, inventory):
    if inventory < 0:
        raise ValueError("Inventory cannot be negative.")

    if forecast < 0:
        raise ValueError("Forecast cannot be negative.")

    return max(0, math.ceil(forecast - inventory))

def evaluate_preparation(prepared, inventory, actual_orders):
    if prepared < 0 or inventory < 0 or actual_orders < 0:
        raise ValueError("Quantities cannot be negative.")

    supply = inventory + prepared

    excess = max(0, supply - actual_orders)
    unmet = max(0, actual_orders - supply)

    return {"excess": excess, "unmet": unmet}

def calculate_loss(excess, unmet, overage_cost, underage_cost):
    if min(excess, unmet, overage_cost, underage_cost) < 0:
        raise ValueError("Quantities and costs cannot be negative.")

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

    if inventory < 0:
        raise ValueError("Inventory cannot be negative.")

    if overage_cost < 0 or underage_cost < 0:
        raise ValueError("Costs cannot be negative.")

    if any(demand < 0 for demand in demand_scenarios):
        raise ValueError("Demand scenarios cannot be negative.")

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

    if any(demand < 0 for demand in demand_scenarios):
        raise ValueError("Demand scenarios cannot be negative.")

    if not 0 <= anchor_index < len(demand_scenarios):
        raise ValueError("Anchor index is out of range.")

    if manager_estimate < 0:
        raise ValueError("Manager estimate cannot be negative.")

    if not 0 <= opinion_weight <= 1:
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
        "custom_anchor": custom_anchor,
        "adjustment": adjustment,
        "updated_scenarios": updated_scenarios,
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