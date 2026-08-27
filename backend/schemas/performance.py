from pydantic import BaseModel


class CreatorPerformanceResponse(BaseModel):
    creator_id: int
    username: str

    followers: int
    average_views: int
    engagement_rate: float

    follower_growth: float
    view_growth: float

    performance_score: float
