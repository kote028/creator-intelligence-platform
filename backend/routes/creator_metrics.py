from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth_dependencies import require_creator
from app.models.social_account import SocialAccount
from app.models.user import User
from app.models.creator_metric import CreatorMetric
from schemas.creator_metric import (
    CreatorMetricCreate,
    CreatorMetricResponse
)


router = APIRouter(
    prefix="/creator-metrics",
    tags=["Creator Metrics"]
)


@router.post(
    "/",
    response_model=CreatorMetricResponse
)
def create_metric(
    metric: CreatorMetricCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
):
    account = db.query(SocialAccount).filter(SocialAccount.account_id == metric.account_id).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Social account not found")
    if current_user.creator is None or account.creator_id != current_user.creator.creator_id:
        raise HTTPException(status_code=403, detail="Creator account access required")
    new_metric = CreatorMetric(
        account_id=metric.account_id,
        followers=metric.followers,
        total_views=metric.total_views,
        total_videos=metric.total_videos,
        avg_views=metric.avg_views,
        total_likes=metric.total_likes,
        total_comments=metric.total_comments,
        engagement_rate=metric.engagement_rate,
        metric_date=metric.metric_date
    )

    db.add(new_metric)
    db.commit()
    db.refresh(new_metric)

    return new_metric


@router.get(
    "/account/{account_id}",
    response_model=list[CreatorMetricResponse]
)
def get_account_metrics(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
):
    account = db.query(SocialAccount).filter(SocialAccount.account_id == account_id).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Social account not found")
    if current_user.creator is None or account.creator_id != current_user.creator.creator_id:
        raise HTTPException(status_code=403, detail="Creator account access required")
    metrics = (
        db.query(CreatorMetric)
        .filter(CreatorMetric.account_id == account_id)
        .order_by(CreatorMetric.metric_date)
        .all()
    )

    return metrics


@router.get(
    "/account/{account_id}/latest",
    response_model=CreatorMetricResponse
)
def get_latest_account_metric(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
):
    account = db.query(SocialAccount).filter(SocialAccount.account_id == account_id).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Social account not found")
    if current_user.creator is None or account.creator_id != current_user.creator.creator_id:
        raise HTTPException(status_code=403, detail="Creator account access required")
    metric = (
        db.query(CreatorMetric)
        .filter(CreatorMetric.account_id == account_id)
        .order_by(CreatorMetric.metric_date.desc(), CreatorMetric.metric_id.desc())
        .first()
    )

    if metric is None:
        raise HTTPException(
            status_code=404,
            detail="No metrics found for this account"
        )

    return metric


@router.delete("/{metric_id}")
def delete_metric(
    metric_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
):
    metric = (
        db.query(CreatorMetric)
        .filter(CreatorMetric.metric_id == metric_id)
        .first()
    )

    if metric is None:
        raise HTTPException(
            status_code=404,
            detail="Metric not found"
        )

    if current_user.creator is None or metric.account.creator_id != current_user.creator.creator_id:
        raise HTTPException(status_code=403, detail="Creator account access required")

    db.delete(metric)
    db.commit()

    return {
        "message": f"Metric {metric_id} successfully deleted"
    }
