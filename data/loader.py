import pandas as pd
import os

_RENAME = {
    "Ticker":                            "company",
    "Fiscal Year":                       "year",
    "Net Profit Margin (%)":             "net_profit_margin",
    "Return on Capital Employed (%)":    "ROCE",
    "Return on Assets (%)":              "ROA",
    "ROE":                               "ROE",
    "Basic EPS (Rs.)":                   "EPS",
    "Earnings Yield":                    "earnings_yield",
    "Enterprise Value (Cr.)":            "enterprise_value",
    "Price/BV (X)":                      "PB",
    "Price/Net Operating Revenue":       "price_to_revenue",
    "Revenue from Operations/Share (Rs.)": "revenue_per_share",
}

_XLSX = os.path.join(os.path.dirname(__file__), "data.xlsx")

def load_dataset() -> pd.DataFrame:
    df = pd.read_excel(_XLSX, usecols=list(_RENAME.keys()))
    df = df.rename(columns=_RENAME)
    df = df.dropna(subset=["company", "year"])
    df["year"] = df["year"].astype(int)
    return df.reset_index(drop=True)

DATASET = load_dataset()

def get_columns() -> list:
    return list(DATASET.columns)

def get_stats(metric: str) -> dict:
    if metric not in DATASET.columns:
        return {}
    s = DATASET[metric].dropna()
    return {
        "min":    round(s.min(), 2),
        "max":    round(s.max(), 2),
        "mean":   round(s.mean(), 2),
        "median": round(s.median(), 2),
    }
