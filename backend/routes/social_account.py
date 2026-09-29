from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth_dependencies import require_creator
from app.models.user import User
from app.models.social_account import SocialAccount
from app.models.creator_metric import CreatorMetric
from app.youtube import YouTubeAPIError, fetch_channel_metrics
from schemas.social_account import (
    SocialAccountCreate,
    SocialAccountUpdate,
    SocialAccountResponse,
    YouTubeSyncResponse,
)


router = APIRouter(
    prefix="/social-accounts",
    tags=["Social Accounts"]
)


@router.post("/", response_model=SocialAccountResponse)
def create_social_account(
    account: SocialAccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
):
    creator = current_user.creator
    if creator is None or creator.creator_id != account.creator_id:
        raise HTTPException(status_code=403, detail="Creator account access required")
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
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
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

    if current_user.creator is None or account.creator_id != current_user.creator.creator_id:
        raise HTTPException(status_code=403, detail="Creator account access required")

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
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
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

    if current_user.creator is None or account.creator_id != current_user.creator.creator_id:
        raise HTTPException(status_code=403, detail="Creator account access required")

    db.delete(account)
    db.commit()

    return {
        "message": f"Social account {account_id} successfully deleted"
    }


@router.post("/{account_id}/sync-youtube", response_model=YouTubeSyncResponse)
def sync_youtube_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
):
    account = db.query(SocialAccount).filter(SocialAccount.account_id == account_id).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Social account not found")
    if current_user.creator is None or account.creator_id != current_user.creator.creator_id:
        raise HTTPException(status_code=403, detail="Creator account access required")
    if account.platform.strip().lower() not in {"youtube", "you tube"}:
        raise HTTPException(status_code=422, detail="This social account is not a YouTube account")

    recent_metric = (
        db.query(CreatorMetric)
        .filter(
            CreatorMetric.account_id == account.account_id,
            CreatorMetric.data_source == "youtube_public",
            CreatorMetric.metric_date == date.today(),
        )
        .order_by(CreatorMetric.metric_id.desc())
        .first()
    )
    if recent_metric:
        return {
            "account_id": account.account_id,
            "channel_id": None,
            "metric_id": recent_metric.metric_id,
            "followers": recent_metric.followers,
            "total_views": recent_metric.total_views,
            "total_videos": recent_metric.total_videos,
            "metric_date": recent_metric.metric_date.isoformat(),
        }

    try:
        values = fetch_channel_metrics(account.username, account.profile_url)
    except YouTubeAPIError as error:
        status_code = 503 if "not configured" in str(error) else 502
        raise HTTPException(status_code=status_code, detail=str(error)) from error

    metric = CreatorMetric(
        account_id=account.account_id,
        followers=values["followers"],
        total_views=values["total_views"],
        total_videos=values["total_posts"],
        avg_views=values["avg_views"],
        total_likes=values["total_likes"],
        total_comments=values["total_comments"],
        engagement_rate=values["engagement_rate"],
        data_source="youtube_public",
        metric_date=date.today(),
    )
    db.add(metric)
    db.commit()
    db.refresh(metric)
    return {
        "account_id": account.account_id,
        "channel_id": values["channel_id"],
        "metric_id": metric.metric_id,
        "followers": metric.followers,
        "total_views": metric.total_views,
        "total_videos": values["total_posts"],
        "metric_date": metric.metric_date.isoformat(),
    }
