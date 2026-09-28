from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class CreatorRecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    creator_id: int
    username: str
    display_name: Optional[str] = None
    niche: Optional[str] = None
    country: Optional[str] = None
    platform: str
    followers: int
    average_views: int
    engagement_rate: float
    follower_growth: float = 0.0
    view_growth: float = 0.0
    performance_score: float
    match_score: float
    reasons: List[str] = []


class CreatorRecommendation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    creator_id: int
    creator_name: str

    niche: Optional[str] = None
    city: Optional[str] = None
    platform: Optional[str] = None

    followers: int
    engagement_rate: float

    marketplace_score: float
