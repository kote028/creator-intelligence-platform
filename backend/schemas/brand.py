from datetime import datetime

from pydantic import BaseModel, EmailStr, ConfigDict


class BrandCreate(BaseModel):
    company_name: str
    email: EmailStr
    website: str | None = None
    industry: str | None = None


class BrandUpdate(BaseModel):
    company_name: str | None = None
    email: EmailStr | None = None
    website: str | None = None
    industry: str | None = None


class BrandResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    brand_id: int
    user_id: int | None = None
    company_name: str
    email: EmailStr
    website: str | None = None
    industry: str | None = None
    created_at: datetime | None = None
