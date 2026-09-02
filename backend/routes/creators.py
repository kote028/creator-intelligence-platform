from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.creator import Creator
from app.models.social_account import SocialAccount
from app.models.creator_metric import CreatorMetric

from schemas.creator import CreatorCreate, CreatorResponse
from schemas.performance import CreatorPerformanceResponse
from schemas.ranking import CreatorRankingResponse

from sqlalchemy import and_
from typing import Optional
from schemas.recommendation import CreatorRecommendation

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
    "/discover",
    response_model=list[CreatorRecommendation]
)
def discover_creators(
    platform: Optional[str] = None,
    niche: Optional[str] = None,
    city: Optional[str] = None,
    min_followers: Optional[int] = None,
    max_followers: Optional[int] = None,
    min_engagement: Optional[float] = None,
    sort_by: str = "performance",
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Search and rank creators using their latest metrics.
    """

    if page < 1:
        raise HTTPException(
            status_code=400,
            detail="page must be >= 1"
        )

    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 100"
        )

    allowed_sorting = {
        "performance",
        "followers",
        "engagement"
    }

    if sort_by not in allowed_sorting:
        raise HTTPException(
            status_code=400,
            detail=(
                "sort_by must be one of: "
                "performance, followers, engagement"
            )
        )

    previous_followers = (
    db.query(
        CreatorMetric.account_id,
        CreatorMetric.followers,
        CreatorMetric.avg_views,
        CreatorMetric.engagement_rate,
        CreatorMetric.metric_date,
        CreatorMetric.metric_id,
    )
        .order_by(
            CreatorMetric.account_id,
            CreatorMetric.metric_date.desc(),
            CreatorMetric.metric_id.desc()
        )
        .all()
    )

    metric_history = {}

    for metric in previous_followers:
        metric_history.setdefault(
            metric.account_id,
            []
        ).append(metric)

    accounts_query = (
        db.query(
            Creator,
            SocialAccount
        )
        .join(
            SocialAccount,
            SocialAccount.creator_id
            == Creator.creator_id
        )
    )

    if platform:
        accounts_query = accounts_query.filter(
            SocialAccount.platform.ilike(platform)
        )

    if niche:
        accounts_query = accounts_query.filter(
            Creator.niche.ilike(niche)
        )

    if city:
        accounts_query = accounts_query.filter(
            Creator.city.ilike(city)
        )

    accounts = accounts_query.all()

    recommendations = []

    for creator, account in accounts:

        metrics = metric_history.get(
            account.account_id,
            []
        )

        if not metrics:
            continue

        latest = metrics[0]

        if (
            min_followers is not None
            and latest.followers < min_followers
        ):
            continue

        if (
            max_followers is not None
            and latest.followers > max_followers
        ):
            continue

        if (
            min_engagement is not None
            and float(latest.engagement_rate or 0)
            < min_engagement
        ):
            continue

        follower_growth = 0.0
        view_growth = 0.0

        if len(metrics) >= 2:

            previous = metrics[1]

            if previous.followers > 0:
                follower_growth = (
                    (
                        latest.followers
                        - previous.followers
                    )
                    / previous.followers
                ) * 100

            if previous.avg_views > 0:
                view_growth = (
                    (
                        latest.avg_views
                        - previous.avg_views
                    )
                    / previous.avg_views
                ) * 100

        view_ratio = 0.0

        if latest.followers > 0:
            view_ratio = (
                latest.avg_views
                / latest.followers
            )

        performance_score = calculate_performance_score(
            engagement_rate=float(
                latest.engagement_rate or 0
            ),
            average_views=int(
                latest.avg_views or 0
            ),
            follower_growth=follower_growth,
            followers=int(
                latest.followers or 0
            ),
            view_ratio=view_ratio
        )

        recommendations.append(
            CreatorRecommendation(
                creator_id=creator.creator_id,
                creator_name=(
                    creator.display_name
                    or creator.username
                    or "Unknown Creator"
                ),
                niche=creator.niche,
                city=creator.city,
                platform=account.platform,
                followers=int(
                    latest.followers or 0
                ),
                engagement_rate=float(
                    latest.engagement_rate or 0
                ),
                marketplace_score=performance_score
            )
        )

    if sort_by == "followers":
        recommendations.sort(
            key=lambda creator: (
                -creator.followers,
                creator.creator_id
            )
        )

    elif sort_by == "engagement":
        recommendations.sort(
            key=lambda creator: (
                -creator.engagement_rate,
                creator.creator_id
            )
        )

    else:
        recommendations.sort(
            key=lambda creator: (
                -creator.marketplace_score,
                -creator.followers,
                creator.creator_id
            )
        )

    start = (page - 1) * limit
    end = start + limit

    return recommendations[start:end]
