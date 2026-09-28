from app.scoring import normalize, calculate_performance_score
from app.matching import normalize_score, calculate_follower_score, calculate_match_score


def test_normalize():
    assert normalize(5, 0, 10) == 50.0
    assert normalize(-5, 0, 10) == 0.0
    assert normalize(15, 0, 10) == 100.0
    assert normalize(10, 10, 10) == 50.0


def test_calculate_performance_score():
    score = calculate_performance_score(
        engagement_rate=5.0,
        average_views=50000,
        follower_growth=10.0,
        followers=100000,
        view_ratio=0.5
    )
    assert 0 <= score <= 100
    assert isinstance(score, float)


def test_calculate_follower_score():
    assert calculate_follower_score(5000, 1000, 10000) == 100.0
    assert calculate_follower_score(500, 1000, 10000) == 0.0
    assert calculate_follower_score(15000, 1000, 10000) == 0.0
    assert calculate_follower_score(5000, None, None) == 100.0


def test_calculate_match_score():
    match_score = calculate_match_score(
        niche_match=100.0,
        country_match=100.0,
        platform_match=100.0,
        engagement_rate=6.0,
        performance_score=85.0,
        follower_score=100.0,
        view_growth=15.0
    )
    assert 0 <= match_score <= 100
    assert isinstance(match_score, float)
