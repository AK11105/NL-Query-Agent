def normalize(values: list) -> list:
    if not values:
        return values
    mn, mx = min(values), max(values)
    if mx == mn:
        return [0.5] * len(values)
    return [round((v - mn) / (mx - mn), 4) for v in values]

NORMALIZE_WHEN = {
    "compare":   True,
    "rank":      True,
    "trend":     False,
    "pct":       False,
}

def should_normalize(intent: list, metric: str) -> bool:
    pct_metrics = {"ROE", "ROCE", "net_profit_margin"}
    if metric in pct_metrics:
        return False
    if "trend" in intent:
        return True   # normalize trend lines for comparison
    if "rank" in intent or "filter" in intent:
        return True
    return False
