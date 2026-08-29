from datetime import datetime

from pydantic import BaseModel, EmailStr, ConfigDict


class BrandCreate(BaseModel):
    company_name: str
    email: EmailStr
    website: str | None = None
    industry: str | None = None


class BrandResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    brand_id: int
    company_name: str
    email: EmailStr
    website: str | None = None
    industry: str | None = None
    created_at: datetime | None = None
