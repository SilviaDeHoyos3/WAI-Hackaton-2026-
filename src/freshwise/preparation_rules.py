from .empirical import recommend_empirical_preparation


def empirical_preparation_rule(forecast, leftovers, context):
    result = recommend_empirical_preparation(
        forecast=forecast,
        inventory=leftovers,
        error_ratios=context["error_ratios"],
        quantile=context["quantile"],
    )
    return result["prepare_qty"]


def make_calibrated_empirical_rule(ratio_lookup, quantile):
    from .empirical_calibration import size_group

    def prepare(forecast, leftovers, context):
        key = (
            context["method"],
            context["window"],
            size_group(forecast),
        )

        if key not in ratio_lookup:
            raise ValueError(f"Missing calibration ratios for {key}")

        return empirical_preparation_rule(
            forecast,
            leftovers,
            {
                "error_ratios": ratio_lookup[key],
                "quantile": quantile,
            },
        )

    return prepare