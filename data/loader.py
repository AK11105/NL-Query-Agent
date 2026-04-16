import pandas as pd
import numpy as np

def load_dataset() -> pd.DataFrame:
    np.random.seed(42)
    companies = ["AlphaCorp", "BetaInc", "GammaTech", "DeltaFin", "EpsilonMfg",
                 "ZetaRetail", "EtaEnergy", "ThetaHealth", "IotaMedia", "KappaAuto"]
    years = [2021, 2022, 2023]
    rows = []
    for company in companies:
        base_roe   = np.random.uniform(5, 35)
        base_roce  = base_roe * np.random.uniform(0.7, 1.1)
        base_npm   = np.random.uniform(3, 25)
        base_pe    = np.random.uniform(8, 40)
        base_pb    = np.random.uniform(1, 6)
        base_rev   = np.random.uniform(500, 5000)
        for year in years:
            noise = lambda: np.random.uniform(-2, 2)
            rows.append({
                "company":           company,
                "year":              year,
                "ROE":               round(base_roe  + noise(), 2),
                "ROCE":              round(base_roce + noise(), 2),
                "net_profit_margin": round(base_npm  + noise(), 2),
                "PE":                round(base_pe   + noise(), 2),
                "PB":                round(base_pb   + noise() * 0.2, 2),
                "revenue":           round(base_rev  * (1 + 0.05 * (year - 2021)) + np.random.uniform(-50, 50), 2),
            })
    return pd.DataFrame(rows)

DATASET = load_dataset()

def get_columns() -> list:
    return list(DATASET.columns)

def get_stats(metric: str) -> dict:
    if metric not in DATASET.columns:
        return {}
    s = DATASET[metric]
    return {"min": round(s.min(), 2), "max": round(s.max(), 2),
            "mean": round(s.mean(), 2), "median": round(s.median(), 2)}
