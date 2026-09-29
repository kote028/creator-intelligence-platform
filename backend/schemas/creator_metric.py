from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import date
from decimal import Decimal


class CreatorMetricCreate(BaseModel):
    account_id: int
    followers: int = Field(default=0, ge=0)
    total_views: int = Field(default=0, ge=0)
    total_videos: int = Field(default=0, ge=0)
    avg_views: int = Field(default=0, ge=0)
    total_likes: int = Field(default=0, ge=0)
    total_comments: int = Field(default=0, ge=0)
    engagement_rate: Decimal = Field(default=Decimal("0.00"), ge=0)
    metric_date: Optional[date] = None


class CreatorMetricResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    metric_id: int
    account_id: int
    followers: int
    total_views: int
    total_videos: int = 0
    avg_views: int
    total_likes: int
    total_comments: int
    engagement_rate: Decimal
    data_source: str = "manual"
    metric_date: Optional[date] = None
