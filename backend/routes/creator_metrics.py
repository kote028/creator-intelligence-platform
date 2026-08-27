from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
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
    db: Session = Depends(get_db)
):
    new_metric = CreatorMetric(
        account_id=metric.account_id,
        followers=metric.followers,
        total_views=metric.total_views,
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
    db: Session = Depends(get_db)
):
    metrics = (
        db.query(CreatorMetric)
        .filter(CreatorMetric.account_id == account_id)
        .order_by(CreatorMetric.metric_date)
        .all()
    )

    return metrics
