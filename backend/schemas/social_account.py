from pydantic import BaseModel, HttpUrl
from typing import Optional


class SocialAccountCreate(BaseModel):
    creator_id: int
    platform: str
    username: str
    profile_url: Optional[HttpUrl] = None
    followers: int = 0
    following: int = 0
    total_posts: int = 0


class SocialAccountResponse(BaseModel):
    account_id: int
    creator_id: int
    platform: str
    username: str
    profile_url: Optional[str] = None
    followers: int
    following: int
    total_posts: int

    class Config:
        from_attributes = True
