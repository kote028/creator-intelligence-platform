from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.creator import Creator
from app.models.social_account import SocialAccount
from app.models.creator_metric import CreatorMetric

from schemas.creator import CreatorCreate, CreatorResponse
from schemas.performance import CreatorPerformanceResponse
from schemas.ranking import CreatorRankingResponse

from app.scoring import calculate_performance_score


router = APIRouter(
    prefix="/creators",
    tags=["Creators"]
)


@router.post("/", response_model=CreatorResponse)
def create_creator(
    creator: CreatorCreate,
    db: Session = Depends(get_db)
):
    new_creator = Creator(
        username=creator.username,
        display_name=creator.display_name,
        email=creator.email,
        bio=creator.bio,
        niche=creator.niche,
        country=creator.country,
        city=creator.city
    )

    db.add(new_creator)
    db.commit()
    db.refresh(new_creator)

    return new_creator


@router.get("/", response_model=list[CreatorResponse])
def get_creators(
    db: Session = Depends(get_db)
):
    creators = db.query(Creator).all()

    return creators


@router.get(
    "/rankings",
    response_model=list[CreatorRankingResponse]
)
def get_creator_rankings(
    db: Session = Depends(get_db)
):
    creators = db.query(Creator).all()

    rankings = []

    for creator in creators:

        accounts = (
            db.query(SocialAccount)
            .filter(
                SocialAccount.creator_id == creator.creator_id
            )
            .all()
        )

        all_metrics = []

        for account in accounts:
            metrics = (
                db.query(CreatorMetric)
                .filter(
                    CreatorMetric.account_id == account.account_id
                )
                .order_by(CreatorMetric.metric_date.asc())
                .all()
            )

            all_metrics.extend(metrics)

        if not all_metrics:
            continue

        all_metrics.sort(
            key=lambda metric: metric.metric_date
        )

        latest = all_metrics[-1]

        follower_growth = 0.0
        view_growth = 0.0

        if len(all_metrics) >= 2:

            previous = all_metrics[-2]

            if previous.followers > 0:
                follower_growth = (
                    (latest.followers - previous.followers)
                    / previous.followers
                ) * 100

            if previous.avg_views > 0:
                view_growth = (
                    (latest.avg_views - previous.avg_views)
                    / previous.avg_views
                ) * 100

        view_ratio = 0.0

        if latest.followers > 0:
            view_ratio = (
                latest.avg_views / latest.followers
            )

        performance_score = calculate_performance_score(
            engagement_rate=float(
                latest.engagement_rate
            ),
            average_views=latest.avg_views,
            follower_growth=follower_growth,
            followers=latest.followers,
            view_ratio=view_ratio
        )

        rankings.append({
            "creator_id": creator.creator_id,
            "username": creator.username,
            "display_name": creator.display_name,
            "niche": creator.niche,
            "country": creator.country,
            "followers": latest.followers,
            "average_views": latest.avg_views,
            "engagement_rate": float(
                latest.engagement_rate
            ),
            "follower_growth": round(
                follower_growth, 2
            ),
            "view_growth": round(
                view_growth, 2
            ),
            "performance_score": performance_score
        })

    rankings.sort(
        key=lambda creator: creator["performance_score"],
        reverse=True
    )

    return rankings


@router.get(
    "/{creator_id}/performance",
    response_model=CreatorPerformanceResponse
)
def get_creator_performance(
    creator_id: int,
    db: Session = Depends(get_db)
):
    creator = (
        db.query(Creator)
        .filter(Creator.creator_id == creator_id)
        .first()
    )

    if creator is None:
        raise HTTPException(
            status_code=404,
            detail="Creator not found"
        )

    accounts = (
        db.query(SocialAccount)
        .filter(
            SocialAccount.creator_id == creator_id
        )
        .all()
    )

    if not accounts:
        raise HTTPException(
            status_code=404,
            detail="No social accounts found"
        )

    all_metrics = []

    for account in accounts:
        metrics = (
            db.query(CreatorMetric)
            .filter(
                CreatorMetric.account_id == account.account_id
            )
            .order_by(CreatorMetric.metric_date.asc())
            .all()
        )

        all_metrics.extend(metrics)

    if not all_metrics:
        raise HTTPException(
            status_code=404,
            detail="No metrics found"
        )

    all_metrics.sort(
        key=lambda metric: metric.metric_date
    )

    latest = all_metrics[-1]

    follower_growth = 0.0
    view_growth = 0.0

    if len(all_metrics) >= 2:

        previous = all_metrics[-2]

        if previous.followers > 0:
            follower_growth = (
                (latest.followers - previous.followers)
                / previous.followers
            ) * 100

        if previous.avg_views > 0:
            view_growth = (
                (latest.avg_views - previous.avg_views)
                / previous.avg_views
            ) * 100

    view_ratio = 0.0

    if latest.followers > 0:
        view_ratio = (
            latest.avg_views / latest.followers
        )

    performance_score = calculate_performance_score(
        engagement_rate=float(
            latest.engagement_rate
        ),
        average_views=latest.avg_views,
        follower_growth=follower_growth,
        followers=latest.followers,
        view_ratio=view_ratio
    )

    return {
        "creator_id": creator.creator_id,
        "username": creator.username,
        "followers": latest.followers,
        "average_views": latest.avg_views,
        "engagement_rate": float(
            latest.engagement_rate
        ),
        "follower_growth": round(
            follower_growth, 2
        ),
        "view_growth": round(
            view_growth, 2
        ),
        "performance_score": performance_score
    }


@router.get(
    "/{creator_id}",
    response_model=CreatorResponse
)
def get_creator(
    creator_id: int,
    db: Session = Depends(get_db)
):
    creator = (
        db.query(Creator)
        .filter(
            Creator.creator_id == creator_id
        )
        .first()
    )

    if creator is None:
        raise HTTPException(
            status_code=404,
            detail="Creator not found"
        )

    return creator
