from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List

from schemas.social_account import SocialAccountResponse


class CreatorCreate(BaseModel):
    username: str
    display_name: Optional[str] = None
    email: Optional[EmailStr] = None
    bio: Optional[str] = None
    niche: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None


class CreatorUpdate(BaseModel):
    display_name: Optional[str] = None
    email: Optional[EmailStr] = None
    bio: Optional[str] = None
    niche: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None


class CreatorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    creator_id: int
    user_id: Optional[int] = None
    username: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    bio: Optional[str] = None
    niche: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None

    social_accounts: List[SocialAccountResponse] = []
