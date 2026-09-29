from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SponsorshipCreate(BaseModel):
    creator_id: int
    campaign_id: int
    agreed_amount: float = Field(gt=0)
    status: Literal["pending"] = "pending"
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class CampaignApplicationCreate(BaseModel):
    campaign_id: int
    agreed_amount: float = Field(gt=0)
    application_message: str | None = Field(default=None, max_length=2000)
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class SponsorshipStatusUpdate(BaseModel):
    status: Literal["accepted", "rejected", "in_progress", "completed", "cancelled"]


class SponsorshipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sponsorship_id: int
    creator_id: int
    campaign_id: int
    agreed_amount: float
    initiated_by: str = "brand"
    application_message: str | None = None
    status: str
    start_date: date | None = None
    end_date: date | None = None
    created_at: datetime | None = None


class CampaignResultUpsert(BaseModel):
    impressions: int = Field(ge=0)
    clicks: int = Field(ge=0)
    conversions: int = Field(ge=0)
    attributed_revenue: float = Field(ge=0)
    reported_at: date

    @model_validator(mode="after")
    def validate_funnel(self):
        if self.clicks > self.impressions:
            raise ValueError("clicks cannot exceed impressions")
        if self.conversions > self.clicks:
            raise ValueError("conversions cannot exceed clicks")
        return self


class CampaignResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    result_id: int
    sponsorship_id: int
    impressions: int
    clicks: int
    conversions: int
    attributed_revenue: float
    reported_at: date
