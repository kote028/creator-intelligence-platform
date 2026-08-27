from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.social_account import SocialAccount
from schemas.social_account import (
    SocialAccountCreate,
    SocialAccountResponse
)


router = APIRouter(
    prefix="/social-accounts",
    tags=["Social Accounts"]
)


@router.post("/", response_model=SocialAccountResponse)
def create_social_account(
    account: SocialAccountCreate,
    db: Session = Depends(get_db)
):
    new_account = SocialAccount(
        creator_id=account.creator_id,
        platform=account.platform,
        username=account.username,
        profile_url=str(account.profile_url) if account.profile_url else None,
        followers=account.followers,
        following=account.following,
        total_posts=account.total_posts
    )

    db.add(new_account)
    db.commit()
    db.refresh(new_account)

    return new_account
