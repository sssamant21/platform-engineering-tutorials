"""Simple, evidence-driven IaC tool-selection scorecard. Scores are illustrative."""
WEIGHTS = {
    "coverage": 20,
    "security": 15,
    "recovery": 15,
    "testing": 15,
    "maintainability": 10,
    "ecosystem": 10,
    "cost": 10,
    "portability": 5,
}

def weighted_score(scores, weights=WEIGHTS):
    if not weights or sum(weights.values()) != 100:
        raise ValueError("Weights must sum to 100")
    if set(scores) != set(weights):
        raise ValueError("Every criterion needs exactly one score")
    if any(not isinstance(s, (int, float)) or isinstance(s, bool) or not 1 <= s <= 5 for s in scores.values()):
        raise ValueError("Scores must be numbers from 1 to 5")
    if any(not isinstance(w, (int, float)) or isinstance(w, bool) or w < 0 for w in weights.values()):
        raise ValueError("Weights must be nonnegative numbers")
    return round(sum(scores[k] * weights[k] for k in weights) / 100, 2)

if __name__ == "__main__":
    examples = {
        "Profile A - hypothetical multi-cloud engine": [5, 4, 4, 4, 4, 5, 4, 4],
        "Profile B - hypothetical AWS-native engine": [4, 5, 4, 4, 4, 4, 5, 2],
        "Profile C - hypothetical configuration engine": [2, 4, 4, 4, 5, 4, 5, 3],
    }
    for label, values in examples.items():
        print(f"{label}: {weighted_score(dict(zip(WEIGHTS, values))):.2f}/5")
