from pydantic import BaseModel


class SemanticCreatorResult(BaseModel):
    creator_id: int
    username: str
    display_name: str | None = None
    bio: str | None = None
    niche: str | None = None
    country: str | None = None
    city: str | None = None
    platform: str | None = None
    followers: int = 0
    average_views: int = 0
    engagement_rate: float = 0
    performance_score: float = 0
    relevance_score: float
    matched_signals: list[str]


class SemanticSearchResponse(BaseModel):
    query: str
    total: int
    indexed_creators: int
    has_more_creators: bool
    page: int
    limit: int
    results: list[SemanticCreatorResult]


class AdvertisingFieldInsight(BaseModel):
    field: str
    fit_score: float
    audience_signals: list[str]
    estimated_views_per_post: int | None = None
    reported_campaigns: int = 0
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    attributed_revenue: float = 0
    click_through_rate: float | None = None
    conversion_rate: float | None = None
    evidence: str


class AdvertisingInsightsResponse(BaseModel):
    creator_id: int
    profile_basis: str
    fields: list[AdvertisingFieldInsight]
    observed_campaigns: int
    impact_note: str
