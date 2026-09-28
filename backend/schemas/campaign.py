from datetime import date

from pydantic import BaseModel, ConfigDict


class CampaignCreate(BaseModel):
    brand_id: int
    campaign_name: str
    description: str | None = None
    budget: float
    start_date: date | None = None
    end_date: date | None = None
    status: str = "active"
    target_niche: str | None = None
    target_country: str | None = None
    target_platform: str | None = None
    min_followers: int | None = None
    max_followers: int | None = None

class CampaignUpdate(BaseModel):
    campaign_name: str | None = None
    description: str | None = None
    budget: float | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = None
    target_niche: str | None = None
    target_country: str | None = None
    target_platform: str | None = None
    min_followers: int | None = None
    max_followers: int | None = None


class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    campaign_id: int
    brand_id: int
    campaign_name: str
    description: str | None = None
    budget: float
    start_date: date | None = None
    end_date: date | None = None
    status: str
    target_niche: str | None = None
    target_country: str | None = None
    target_platform: str | None = None
    min_followers: int | None = None
    max_followers: int | None = None
