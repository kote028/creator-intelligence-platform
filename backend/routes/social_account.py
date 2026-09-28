from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.social_account import SocialAccount
from schemas.social_account import (
    SocialAccountCreate,
    SocialAccountUpdate,
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


@router.get("/creator/{creator_id}", response_model=list[SocialAccountResponse])
def get_creator_social_accounts(
    creator_id: int,
    db: Session = Depends(get_db)
):
    return (
        db.query(SocialAccount)
        .filter(SocialAccount.creator_id == creator_id)
        .all()
    )


@router.get("/{account_id}", response_model=SocialAccountResponse)
def get_social_account(
    account_id: int,
    db: Session = Depends(get_db)
):
    account = (
        db.query(SocialAccount)
        .filter(SocialAccount.account_id == account_id)
        .first()
    )

    if account is None:
        raise HTTPException(
            status_code=404,
            detail="Social account not found"
        )

    return account


@router.put("/{account_id}", response_model=SocialAccountResponse)
def update_social_account(
    account_id: int,
    account_update: SocialAccountUpdate,
    db: Session = Depends(get_db)
):
    account = (
        db.query(SocialAccount)
        .filter(SocialAccount.account_id == account_id)
        .first()
    )

    if account is None:
        raise HTTPException(
            status_code=404,
            detail="Social account not found"
        )

    update_dict = account_update.model_dump(exclude_unset=True)
    if "profile_url" in update_dict and update_dict["profile_url"] is not None:
        update_dict["profile_url"] = str(update_dict["profile_url"])

    for field, value in update_dict.items():
        setattr(account, field, value)

    db.commit()
    db.refresh(account)

    return account


@router.delete("/{account_id}")
def delete_social_account(
    account_id: int,
    db: Session = Depends(get_db)
):
    account = (
        db.query(SocialAccount)
        .filter(SocialAccount.account_id == account_id)
        .first()
    )

    if account is None:
        raise HTTPException(
            status_code=404,
            detail="Social account not found"
        )

    db.delete(account)
    db.commit()

    return {
        "message": f"Social account {account_id} successfully deleted"
    }
