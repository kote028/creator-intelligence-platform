from pydantic import BaseModel
from typing import Optional
from datetime import date
from decimal import Decimal


class CreatorMetricCreate(BaseModel):
    account_id: int
    followers: int = 0
    total_views: int = 0
    avg_views: int = 0
    total_likes: int = 0
    total_comments: int = 0
    engagement_rate: Decimal = Decimal("0.00")
    metric_date: Optional[date] = None


class CreatorMetricResponse(BaseModel):
    metric_id: int
    account_id: int
    followers: int
    total_views: int
    avg_views: int
    total_likes: int
    total_comments: int
    engagement_rate: Decimal
    metric_date: Optional[date] = None

    class Config:
        from_attributes = True
