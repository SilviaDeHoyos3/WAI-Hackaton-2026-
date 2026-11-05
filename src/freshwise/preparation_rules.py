from .empirical import recommend_empirical_preparation


def empirical_preparation_rule(forecast, leftovers, context):
    result = recommend_empirical_preparation(
        forecast=forecast,
        inventory=leftovers,
        error_ratios=context["error_ratios"],
        quantile=context["quantile"],
    )
    return result["prepare_qty"]