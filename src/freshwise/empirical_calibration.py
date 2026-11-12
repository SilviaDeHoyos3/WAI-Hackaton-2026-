import numpy as np

WINDOWS = {
    "A": ((96, 105), (106, 115)),
    "B": ((116, 125), (126, 135)),
}


def size_group(forecast):
    return int(np.searchsorted([69.0, 230.0], forecast, side="right"))


def build_ratio_lookup(rows, methods=("last", "blend", "hgb")):
    """Build ratios using calibration outcomes only."""
    lookup = {}

    for method in methods:
        for window, (cal_weeks, eval_weeks) in WINDOWS.items():
            subset = rows[
                (rows["method"] == method)
                & (rows["window"] == window)
            ]
            cal = subset[subset["role"] == "calibration"]
            evaluation = subset[subset["role"] == "evaluation"]

            if cal.empty or evaluation.empty:
                raise ValueError(
                    f"Missing calibration or evaluation rows: {method}, {window}"
                )

            if not cal["target_week"].between(*cal_weeks).all():
                raise ValueError("Unexpected calibration weeks.")

            if not evaluation["target_week"].between(*eval_weeks).all():
                raise ValueError("Unexpected evaluation weeks.")

            assert (
                cal["target_week"].max()
                < evaluation["target_week"].min()
            ), "Calibration must precede evaluation."

            forecasts = cal["forecast_orders"].to_numpy(dtype=float)
            actuals = cal["actual_orders"].to_numpy(dtype=float)

            if (
                not np.isfinite(forecasts).all()
                or not np.isfinite(actuals).all()
                or (forecasts < 0).any()
                or (actuals < 0).any()
            ):
                raise ValueError("Invalid calibration forecasts or orders.")

            positive = forecasts > 0
            forecasts = forecasts[positive]
            ratios = actuals[positive] / forecasts
            groups = np.searchsorted(
                [69.0, 230.0], forecasts, side="right"
            )

            if not np.isfinite(ratios).all():
                raise ValueError("Calibration ratios must be finite.")

            for group in range(3):
                sample = ratios[groups == group]
                if sample.size == 0:
                    raise ValueError(
                        f"Empty calibration group: {method}, {window}, {group}"
                    )
                lookup[(method, window, group)] = sample

    return lookup