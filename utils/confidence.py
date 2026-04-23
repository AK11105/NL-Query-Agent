def compute_confidence(clarifications: int, retries: int, overrides: int) -> float:
    score = 1.0 - 0.1 * clarifications - 0.1 * retries - 0.05 * overrides
    return round(max(score, 0.0), 2)
