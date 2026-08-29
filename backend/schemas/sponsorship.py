from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class SponsorshipCreate(BaseModel):
    creator_id: int
    campaign_id: int
    agreed_amount: float
    status: str = "pending"
    start_date: date | None = None
    end_date: date | None = None


class SponsorshipStatusUpdate(BaseModel):
    status: str


class SponsorshipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sponsorship_id: int
    creator_id: int
    campaign_id: int
    agreed_amount: float
    status: str
    start_date: date | None = None
    end_date: date | None = None
    created_at: datetime | None = None

