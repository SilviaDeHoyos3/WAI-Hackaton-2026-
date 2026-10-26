from pathlib import Path
from .data import load_data, audit, enrich
from .forecast import backtest

def main():
    tables = load_data()
    print(audit(tables).to_string(index=False))
    train = enrich(tables["train.csv"], tables["meal_info.csv"], tables["fulfilment_center_info.csv"])
    scores = backtest(train)
    print(scores.to_string(index=False))
    out = Path("outputs")
    out.mkdir(exist_ok=True)
    scores.to_csv(out / "baseline_backtests.csv", index=False)

if __name__ == "__main__":
    main()
