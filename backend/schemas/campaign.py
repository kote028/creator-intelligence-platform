from datetime import date

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CampaignCreate(BaseModel):
    brand_id: int
    campaign_name: str
    description: str | None = None
    budget: float = Field(gt=0)
    start_date: date | None = None
    end_date: date | None = None
    status: Literal["draft", "active", "paused", "completed", "cancelled"] = "active"
    target_niche: str | None = None
    advertising_field: str | None = None
    target_country: str | None = None
    target_platform: str | None = None
    min_followers: int | None = Field(default=None, ge=0)
    max_followers: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_campaign_range(self):
        if self.min_followers is not None and self.max_followers is not None and self.min_followers > self.max_followers:
            raise ValueError("min_followers must not exceed max_followers")
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self

class CampaignUpdate(BaseModel):
    campaign_name: str | None = None
    description: str | None = None
    budget: float | None = Field(default=None, gt=0)
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = None
    target_niche: str | None = None
    advertising_field: str | None = None
    target_country: str | None = None
    target_platform: str | None = None
    min_followers: int | None = Field(default=None, ge=0)
    max_followers: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_campaign_range(self):
        if self.min_followers is not None and self.max_followers is not None and self.min_followers > self.max_followers:
            raise ValueError("min_followers must not exceed max_followers")
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


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
    advertising_field: str | None = None
    target_country: str | None = None
    target_platform: str | None = None
    min_followers: int | None = None
    max_followers: int | None = None
