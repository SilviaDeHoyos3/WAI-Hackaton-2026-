from pathlib import Path
import os
import pandas as pd

FILES = ("train.csv", "test.csv", "meal_info.csv", "fulfilment_center_info.csv",
         "sample_submission.csv", "Emissions intensities.csv", "TPFLW.csv")

def data_dir(path=None):
    candidates = [Path(path)] if path else ([Path(os.environ["FRESHWISE_DATA_DIR"])]
        if os.environ.get("FRESHWISE_DATA_DIR") else [Path(__file__).resolve().parents[2] / "data",
        Path.home() / "Library/Mobile Documents/com~apple~CloudDocs/Canada/UBC/AI Woman Hackaton/Data"])
    for candidate in candidates:
        if all((candidate / name).is_file() for name in FILES):
            return candidate
    raise FileNotFoundError("Set FRESHWISE_DATA_DIR to the folder containing all seven source CSVs.")

def load_data(path=None):
    root = data_dir(path)
    return {name: pd.read_csv(root / name, dtype={"Item Code (CPC)": str,
        "Area Code (M49)": str} if name.startswith("Emissions") else
        {"cpc_code": str, "m49_code": str} if name == "TPFLW.csv" else None,
        low_memory=False) for name in FILES}

def audit(tables):
    return pd.DataFrame([{"file": name, "rows": len(df), "columns": len(df.columns),
        "missing_cells": int(df.isna().sum().sum()), "duplicate_rows": int(df.duplicated().sum())}
        for name, df in tables.items()])

def enrich(orders, meals, centers):
    result = orders.merge(meals, on="meal_id", how="left", validate="many_to_one")
    result = result.merge(centers, on="center_id", how="left", validate="many_to_one")
    if result[["category", "center_type"]].isna().any().any():
        raise ValueError("Unmatched meal or center identifiers")
    return result
