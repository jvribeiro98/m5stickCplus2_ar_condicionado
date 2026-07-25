"""Pontuações determinísticas de confiança."""


def clamp(value: float) -> float:
    """Limita e arredonda confiança para quatro casas."""
    return round(max(0.0, min(1.0, value)), 4)


def level(value: float) -> str:
    if value >= 0.95:
        return "deterministic"
    if value >= 0.80:
        return "strong"
    if value >= 0.60:
        return "probable"
    if value >= 0.40:
        return "ambiguous"
    return "review_only"
