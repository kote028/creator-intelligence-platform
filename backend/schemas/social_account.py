from pydantic import BaseModel, HttpUrl, ConfigDict
from typing import Optional


class SocialAccountCreate(BaseModel):
    creator_id: int
    platform: str
    username: str
    profile_url: Optional[HttpUrl] = None
    followers: int = 0
    following: int = 0
    total_posts: int = 0


class SocialAccountUpdate(BaseModel):
    platform: Optional[str] = None
    username: Optional[str] = None
    profile_url: Optional[HttpUrl] = None
    followers: Optional[int] = None
    following: Optional[int] = None
    total_posts: Optional[int] = None


class SocialAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account_id: int
    creator_id: int
    platform: str
    username: str
    profile_url: Optional[str] = None
    followers: int
    following: int
    total_posts: int
