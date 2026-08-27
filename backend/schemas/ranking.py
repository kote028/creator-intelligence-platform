from pydantic import BaseModel


class CreatorRankingResponse(BaseModel):
    creator_id: int
    username: str
    display_name: str | None = None
    niche: str | None = None
    country: str | None = None

    followers: int
    average_views: int
    engagement_rate: float
    follower_growth: float
    view_growth: float

    performance_score: float
