def normalize_score(
    value: float,
    minimum: float,
    maximum: float
) -> float:

    if maximum == minimum:
        return 50.0

    score = (
        (value - minimum)
        / (maximum - minimum)
    ) * 100

    return max(0.0, min(100.0, score))


def calculate_follower_score(
    followers: int,
    minimum: int | None,
    maximum: int | None
) -> float:

    if minimum is not None and followers < minimum:
        return 0.0

    if maximum is not None and followers > maximum:
        return 0.0

    return 100.0


def calculate_match_score(
    niche_match: float,
    country_match: float,
    platform_match: float,
    engagement_rate: float,
    performance_score: float,
    follower_score: float,
    view_growth: float
) -> float:

    engagement_score = normalize_score(
        engagement_rate,
        0,
        10
    )

    growth_score = normalize_score(
        view_growth,
        -20,
        50
    )

    final_score = (
        niche_match * 0.25
        + country_match * 0.15
        + platform_match * 0.15
        + engagement_score * 0.15
        + performance_score * 0.15
        + follower_score * 0.10
        + growth_score * 0.05
    )

    return round(final_score, 2)
