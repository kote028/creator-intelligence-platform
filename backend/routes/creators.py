from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.creator import Creator
from app.models.social_account import SocialAccount
from app.models.creator_metric import CreatorMetric

from app.models.user import User
from app.auth_dependencies import get_current_user, require_creator

from schemas.creator import CreatorCreate, CreatorUpdate, CreatorResponse, PublicCreatorResponse
from schemas.performance import CreatorPerformanceResponse
from schemas.ranking import CreatorRankingResponse

from sqlalchemy import and_
from typing import Optional
from schemas.recommendation import CreatorRecommendation
from schemas.intelligence import (
    AdvertisingFieldInsight,
    AdvertisingInsightsResponse,
    SemanticCreatorResult,
    SemanticSearchResponse,
    CreatorDirectoryItem,
    CreatorDirectoryResponse,
)
from app.advertising import ADVERTISING_FIELDS, creator_document
from app.semantic_search import keyword_overlap, semantic_scores
from app.models.sponsorship import Sponsorship
from app.models.campaign_result import CampaignResult
from app.models.campaign import Campaign

from app.scoring import calculate_performance_score


router = APIRouter(
    prefix="/creators",
    tags=["Creators"]
)


@router.post("/", response_model=CreatorResponse)
def create_creator(
    creator: CreatorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
):
    if current_user.creator:
        raise HTTPException(status_code=400, detail="Creator profile already exists for this account")
    existing = db.query(Creator).filter(Creator.username == creator.username).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Username already taken"
        )

    new_creator = Creator(
        user_id=current_user.user_id,
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


@router.get("/me", response_model=CreatorResponse)
def get_my_creator_profile(
    current_user: User = Depends(require_creator),
    db: Session = Depends(get_db)
):
    if not current_user.creator:
        raise HTTPException(
            status_code=404,
            detail="Creator profile not found for this account"
        )
    return current_user.creator


@router.put("/me", response_model=CreatorResponse)
def update_my_creator_profile(
    update_data: CreatorUpdate,
    current_user: User = Depends(require_creator),
    db: Session = Depends(get_db)
):
    creator = current_user.creator
    if not creator:
        raise HTTPException(
            status_code=404,
            detail="Creator profile not found for this account"
        )
    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(creator, field, value)
    db.commit()
    db.refresh(creator)
    return creator


@router.post("/me", response_model=CreatorResponse)
def create_my_creator_profile(
    creator: CreatorCreate,
    current_user: User = Depends(require_creator),
    db: Session = Depends(get_db)
):
    if current_user.creator:
        raise HTTPException(
            status_code=400,
            detail="Creator profile already exists for this account"
        )
    existing = db.query(Creator).filter(Creator.username == creator.username).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Username already taken"
        )
    new_creator = Creator(
        user_id=current_user.user_id,
        username=creator.username,
        display_name=creator.display_name,
        email=creator.email or current_user.email,
        bio=creator.bio,
        niche=creator.niche,
        country=creator.country,
        city=creator.city
    )
    db.add(new_creator)
    db.commit()
    db.refresh(new_creator)
    return new_creator


@router.get("/", response_model=list[PublicCreatorResponse])
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
                    CreatorMetric.account_id == account.account_id,
                    CreatorMetric.data_source != "youtube_public",
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
            "city": creator.city,
            "platform": latest.account.platform if latest.account else None,
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


@router.get("/directory", response_model=CreatorDirectoryResponse)
def creator_directory(
    q: Optional[str] = Query(default=None, max_length=240),
    niche: Optional[str] = Query(default=None, max_length=100),
    platform: Optional[str] = Query(default=None, max_length=50),
    creator_ids: list[int] = Query(default=[]),
    saved_only: bool = Query(default=False),
    sort_by: str = Query(default="recommended", pattern="^(recommended|followers|engagement|name)$"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=24, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Browse every creator profile, including profiles without metric snapshots."""
    creators = (
        db.query(Creator)
        .options(selectinload(Creator.social_accounts))
        .order_by(Creator.creator_id)
        .all()
    )
    account_ids = [account.account_id for creator in creators for account in creator.social_accounts]
    latest_metrics = {}
    if account_ids:
        rows = (
            db.query(CreatorMetric)
            .filter(
                CreatorMetric.account_id.in_(account_ids),
                CreatorMetric.data_source != "youtube_public",
            )
            .order_by(CreatorMetric.metric_date.desc(), CreatorMetric.metric_id.desc())
            .all()
        )
        for row in rows:
            latest_metrics.setdefault(row.account_id, row)

    documents = [creator_document(creator, creator.social_accounts) for creator in creators]
    scores = semantic_scores(q, documents) if q and len(q.strip()) >= 2 and documents else [0.0] * len(creators)
    niches = sorted({creator.niche for creator in creators if creator.niche})
    platforms = sorted({account.platform for creator in creators for account in creator.social_accounts if account.platform})
    if saved_only and not creator_ids:
        creators = []
        documents = []
        scores = []
    elif creator_ids:
        allowed_ids = set(creator_ids)
        selected = [(creator, document, score) for creator, document, score in zip(creators, documents, scores) if creator.creator_id in allowed_ids]
        creators = [entry[0] for entry in selected]
        documents = [entry[1] for entry in selected]
        scores = [entry[2] for entry in selected]
    items = []
    for creator, document, score in zip(creators, documents, scores):
        accounts = creator.social_accounts
        if niche and niche.casefold() not in (creator.niche or "").casefold():
            continue
        if platform and not any(platform.casefold() in account.platform.casefold() for account in accounts):
            continue
        if q and len(q.strip()) >= 2 and score <= 0:
            continue
        if q and len(q.strip()) < 2 and q.casefold() not in document.casefold():
            continue
        account, metric = max(
            ((account, latest_metrics.get(account.account_id)) for account in accounts),
            key=lambda pair: (
                pair[1].avg_views if pair[1] else 0,
                pair[1].followers if pair[1] else pair[0].followers or 0,
            ),
            default=(None, None),
        )
        followers = int(metric.followers if metric else account.followers if account else 0)
        avg_views = int(metric.avg_views or 0) if metric else 0
        engagement = float(metric.engagement_rate or 0) if metric else 0.0
        performance = calculate_performance_score(
            engagement_rate=engagement,
            average_views=avg_views,
            follower_growth=0,
            followers=followers,
            view_ratio=(avg_views / followers if followers else 0),
        ) if metric else 0.0
        items.append(CreatorDirectoryItem(
            creator_id=creator.creator_id,
            username=creator.username,
            display_name=creator.display_name,
            bio=creator.bio,
            niche=creator.niche,
            country=creator.country,
            city=creator.city,
            platform=account.platform if account else None,
            followers=followers,
            average_views=avg_views,
            engagement_rate=engagement,
            performance_score=performance,
            has_metrics=metric is not None,
            relevance_score=round(max(0, min(1, score)) * 100, 1) if q and len(q.strip()) >= 2 else None,
        ))

    if sort_by == "followers":
        items.sort(key=lambda item: (-item.followers, item.creator_id))
    elif sort_by == "engagement":
        items.sort(key=lambda item: (-item.engagement_rate, item.creator_id))
    elif sort_by == "name":
        items.sort(key=lambda item: (item.display_name or item.username).casefold())
    elif q and len(q.strip()) >= 2:
        items.sort(key=lambda item: (-(item.relevance_score or 0), -item.performance_score, item.creator_id))
    else:
        items.sort(key=lambda item: (-item.performance_score, -item.followers, item.creator_id))

    total = len(items)
    start = (page - 1) * limit
    return CreatorDirectoryResponse(
        page=page,
        limit=limit,
        total=total,
        total_pages=(total + limit - 1) // limit,
        niches=niches,
        platforms=platforms,
        results=items[start:start + limit],
    )


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
                CreatorMetric.account_id == account.account_id,
                CreatorMetric.data_source != "youtube_public",
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
        .filter(CreatorMetric.data_source != "youtube_public")
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


@router.get("/semantic-search", response_model=SemanticSearchResponse)
def semantic_creator_search(
    q: str = Query(min_length=2, max_length=240),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    creators = (
        db.query(Creator)
        .options(selectinload(Creator.social_accounts))
        .order_by(Creator.creator_id)
        .limit(5000)
        .all()
    )
    documents = [creator_document(creator, creator.social_accounts) for creator in creators]
    scores = semantic_scores(q, documents)
    account_ids = [account.account_id for creator in creators for account in creator.social_accounts]
    latest_metrics = {}
    if account_ids:
        metrics = (
            db.query(CreatorMetric)
            .filter(
                CreatorMetric.account_id.in_(account_ids),
                CreatorMetric.data_source != "youtube_public",
            )
            .order_by(CreatorMetric.metric_date.desc(), CreatorMetric.metric_id.desc())
            .all()
        )
        for metric in metrics:
            latest_metrics.setdefault(metric.account_id, metric)

    ranked = []
    for creator, document, score in zip(creators, documents, scores):
        if score <= 0:
            continue
        account_data = []
        for account in creator.social_accounts:
            metric = latest_metrics.get(account.account_id)
            account_data.append((account, metric))
        account, metric = max(
            account_data,
            key=lambda pair: (pair[1].avg_views if pair[1] else 0, pair[0].followers),
            default=(None, None),
        )
        followers = int(metric.followers if metric else account.followers if account else 0)
        avg_views = int(metric.avg_views if metric else 0)
        engagement = float(metric.engagement_rate if metric else 0)
        performance = calculate_performance_score(
            engagement_rate=engagement,
            average_views=avg_views,
            follower_growth=0,
            followers=followers,
            view_ratio=(avg_views / followers if followers else 0),
        ) if metric else 0
        ranked.append((score, SemanticCreatorResult(
            creator_id=creator.creator_id,
            username=creator.username,
            display_name=creator.display_name,
            bio=creator.bio,
            niche=creator.niche,
            country=creator.country,
            city=creator.city,
            platform=account.platform if account else None,
            followers=followers,
            average_views=avg_views,
            engagement_rate=engagement,
            performance_score=performance,
            relevance_score=round(max(0, min(1, score)) * 100, 1),
            matched_signals=keyword_overlap(q, document) or ["Latent topic similarity"],
        )))
    ranked.sort(key=lambda item: (item[0], item[1].performance_score), reverse=True)
    offset = (page - 1) * limit
    return SemanticSearchResponse(
        query=q,
        total=len(ranked),
        indexed_creators=len(creators),
        has_more_creators=len(creators) == 5000,
        page=page,
        limit=limit,
        results=[result for _, result in ranked[offset:offset + limit]],
    )


@router.get("/me/advertising-insights", response_model=AdvertisingInsightsResponse)
def get_my_advertising_insights(
    current_user: User = Depends(require_creator),
    db: Session = Depends(get_db),
):
    creator = current_user.creator
    if creator is None:
        raise HTTPException(status_code=404, detail="Create your creator profile before requesting insights")
    accounts = db.query(SocialAccount).filter(SocialAccount.creator_id == creator.creator_id).all()
    document = creator_document(creator, accounts)
    if len(document.split()) < 2:
        raise HTTPException(status_code=422, detail="Add a bio or niche to get advertising field insights")

    fields = list(ADVERTISING_FIELDS)
    similarities = semantic_scores(document, [ADVERTISING_FIELDS[field] for field in fields])
    metrics = []
    account_ids = [account.account_id for account in accounts]
    if account_ids:
        metrics = (
            db.query(CreatorMetric)
            .filter(
                CreatorMetric.account_id.in_(account_ids),
                CreatorMetric.data_source != "youtube_public",
            )
            .order_by(CreatorMetric.metric_date.desc(), CreatorMetric.metric_id.desc())
            .all()
        )
    latest_by_account = {}
    for metric in metrics:
        latest_by_account.setdefault(metric.account_id, metric)
    average_views = max((int(metric.avg_views) for metric in latest_by_account.values()), default=0)
    engagement = max((float(metric.engagement_rate or 0) for metric in latest_by_account.values()), default=0)

    sponsorships = (
        db.query(Sponsorship)
        .join(Campaign)
        .outerjoin(
            CampaignResult,
            CampaignResult.sponsorship_id == Sponsorship.sponsorship_id,
        )
        .filter(Sponsorship.creator_id == creator.creator_id)
        .all()
    )
    observed: dict[str, dict] = {}
    for sponsorship in sponsorships:
        result = sponsorship.result
        field = sponsorship.campaign.advertising_field or sponsorship.campaign.target_niche or "Other / uncategorized"
        row = observed.setdefault(field.casefold(), {
            "field": field,
            "campaigns": 0,
            "impressions": 0,
            "clicks": 0,
            "conversions": 0,
            "revenue": 0.0,
        })
        if result:
            row["campaigns"] += 1
            row["impressions"] += int(result.impressions)
            row["clicks"] += int(result.clicks)
            row["conversions"] += int(result.conversions)
            row["revenue"] += float(result.attributed_revenue)

    insights = []
    for field, score in zip(fields, similarities):
        historical = observed.get(field.casefold(), {})
        signals = []
        if creator.niche:
            signals.append(f"Profile niche: {creator.niche}")
        if engagement:
            signals.append(f"Engagement rate: {engagement:.1f}%")
        if average_views:
            signals.append(f"Typical views per post: {average_views:,}")
        impressions = historical.get("impressions", 0)
        clicks = historical.get("clicks", 0)
        conversions = historical.get("conversions", 0)
        insights.append(AdvertisingFieldInsight(
            field=field,
            fit_score=round(max(0, min(1, score)) * 100, 1),
            audience_signals=signals[:3],
            estimated_views_per_post=average_views or None,
            reported_campaigns=historical.get("campaigns", 0),
            impressions=impressions,
            clicks=clicks,
            conversions=conversions,
            attributed_revenue=round(historical.get("revenue", 0), 2),
            click_through_rate=round(clicks / impressions * 100, 2) if impressions else None,
            conversion_rate=round(conversions / clicks * 100, 2) if clicks else None,
            evidence=("Brand-reported campaign outcomes and profile fit." if historical.get("campaigns") else "Profile fit estimate only; no campaign outcome reports are available for this field."),
        ))
    insights.sort(key=lambda item: (item.reported_campaigns > 0, item.fit_score), reverse=True)
    return AdvertisingInsightsResponse(
        creator_id=creator.creator_id,
        profile_basis=document,
        fields=insights[:5],
        observed_campaigns=sum(item["campaigns"] for item in observed.values()),
        impact_note="Field fit is inferred from profile text. Impressions, clicks, conversions, and attributed revenue are brand-reported outcomes; fit score is not a prediction of sales or ad lift.",
    )


@router.get("/{creator_id}", response_model=PublicCreatorResponse)
def get_creator(
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

    return creator


@router.put("/{creator_id}", response_model=CreatorResponse)
def update_creator(
    creator_id: int,
    creator_update: CreatorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
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

    if current_user.creator is None or current_user.creator.creator_id != creator_id:
        raise HTTPException(status_code=403, detail="Creator account access required")

    for field, value in creator_update.model_dump(exclude_unset=True).items():
        setattr(creator, field, value)

    db.commit()
    db.refresh(creator)

    return creator


@router.delete("/{creator_id}")
def delete_creator(
    creator_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
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

    if current_user.creator is None or current_user.creator.creator_id != creator_id:
        raise HTTPException(status_code=403, detail="Creator account access required")

    db.delete(creator)
    db.commit()

    return {
        "message": f"Creator {creator_id} successfully deleted"
    }
