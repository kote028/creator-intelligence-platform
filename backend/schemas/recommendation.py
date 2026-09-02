from pydantic import BaseModel
from typing import Optional


class CreatorRecommendationResponse(BaseModel):
    creator_id: int
    creator_name: str
    platform: str
    followers: int
    performance_score: float
    match_score: float
    follower_score: float

    class Config:
        from_attributes = True


class CreatorRecommendation(BaseModel):
    creator_id: int
    creator_name: str

    niche: Optional[str] = None
    city: Optional[str] = None
    platform: Optional[str] = None

    followers: int
    engagement_rate: float

    marketplace_score: float

    class Config:
        from_attributes = True
