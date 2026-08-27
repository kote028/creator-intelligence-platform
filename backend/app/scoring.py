def normalize(value: float, minimum: float, maximum: float) -> float:
    if maximum == minimum:
        return 50.0

    score = ((value - minimum) / (maximum - minimum)) * 100

    return max(0.0, min(100.0, score))


def calculate_performance_score(
    engagement_rate: float,
    average_views: int,
    follower_growth: float,
    followers: int,
    view_ratio: float
) -> float:

    engagement_score = normalize(
        engagement_rate,
        0,
        10
    )

    view_score = normalize(
        average_views,
        0,
        100000
    )

    growth_score = normalize(
        follower_growth,
        -10,
        30
    )

    audience_score = normalize(
        followers,
        0,
        200000
    )

    view_ratio_score = normalize(
        view_ratio,
        0,
        1
    )

    final_score = (
        engagement_score * 0.30
        + view_score * 0.25
        + growth_score * 0.20
        + audience_score * 0.15
        + view_ratio_score * 0.10
    )

    return round(final_score, 2)
