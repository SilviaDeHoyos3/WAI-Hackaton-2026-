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