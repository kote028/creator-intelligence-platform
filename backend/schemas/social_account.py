from pydantic import BaseModel, HttpUrl, ConfigDict, Field
from typing import Optional


class SocialAccountCreate(BaseModel):
    creator_id: int
    platform: str = Field(min_length=2, max_length=50)
    username: str = Field(min_length=1, max_length=100)
    profile_url: Optional[HttpUrl] = None
    followers: int = Field(default=0, ge=0)
    following: int = Field(default=0, ge=0)
    total_posts: int = Field(default=0, ge=0)


class YouTubeSyncResponse(BaseModel):
    account_id: int
    channel_id: str | None = None
    metric_id: int
    followers: int
    total_views: int
    total_videos: int
    metric_date: str


class SocialAccountUpdate(BaseModel):
    platform: Optional[str] = None
    username: Optional[str] = None
    profile_url: Optional[HttpUrl] = None
    followers: Optional[int] = Field(default=None, ge=0)
    following: Optional[int] = Field(default=None, ge=0)
    total_posts: Optional[int] = Field(default=None, ge=0)


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
