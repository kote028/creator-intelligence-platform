from app.models.creator import Creator
from app.models.social_account import SocialAccount
from app.models.creator_metric import CreatorMetric

from app.scoring import calculate_performance_score

from app.matching import (
    calculate_match_score,
    calculate_follower_score
)

from schemas.recommendation import (
    CreatorRecommendationResponse
)
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.campaign import Campaign
from app.models.brand import Brand

from schemas.campaign import (
    CampaignCreate,
    CampaignResponse
)


router = APIRouter(
    prefix="/campaigns",
    tags=["Campaigns"]
)


@router.post(
    "/",
    response_model=CampaignResponse
)
def create_campaign(
    campaign: CampaignCreate,
    db: Session = Depends(get_db)
):
    brand = (
        db.query(Brand)
        .filter(Brand.brand_id == campaign.brand_id)
        .first()
    )

    if brand is None:
        raise HTTPException(
            status_code=404,
            detail="Brand not found"
        )

    new_campaign = Campaign(
        brand_id=campaign.brand_id,
        campaign_name=campaign.campaign_name,
        description=campaign.description,
        budget=campaign.budget,
        start_date=campaign.start_date,
        end_date=campaign.end_date,
        status=campaign.status,
        target_niche=campaign.target_niche,
        target_country=campaign.target_country,
        target_platform=campaign.target_platform,
        min_followers=campaign.min_followers,
        max_followers=campaign.max_followers
    )

    db.add(new_campaign)
    db.commit()
    db.refresh(new_campaign)

    return new_campaign


@router.get(
    "/",
    response_model=list[CampaignResponse]
)
def get_campaigns(
    db: Session = Depends(get_db)
):
    return db.query(Campaign).all()


@router.get(
    "/{campaign_id}",
    response_model=CampaignResponse
)
def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db)
):
    campaign = (
        db.query(Campaign)
        .filter(
            Campaign.campaign_id == campaign_id
        )
        .first()
    )

    if campaign is None:
        raise HTTPException(
            status_code=404,
            detail="Campaign not found"
        )

    return campaign


@router.get(
    "/brand/{brand_id}",
    response_model=list[CampaignResponse]
)
def get_brand_campaigns(
    brand_id: int,
    db: Session = Depends(get_db)
):
    brand = (
        db.query(Brand)
        .filter(Brand.brand_id == brand_id)
        .first()
    )

    if brand is None:
        raise HTTPException(
            status_code=404,
            detail="Brand not found"
        )

    return (
        db.query(Campaign)
        .filter(Campaign.brand_id == brand_id)
        .all()
    )
@router.get(
    "/{campaign_id}/recommendations",
    response_model=list[CreatorRecommendationResponse]
)
def get_campaign_recommendations(
    campaign_id: int,
    db: Session = Depends(get_db)
):

    campaign = (
        db.query(Campaign)
        .filter(
            Campaign.campaign_id == campaign_id
        )
        .first()
    )

    if campaign is None:
        raise HTTPException(
            status_code=404,
            detail="Campaign not found"
        )

    creators = db.query(Creator).all()

    recommendations = []

    for creator in creators:

        accounts = (
            db.query(SocialAccount)
            .filter(
                SocialAccount.creator_id
                == creator.creator_id
            )
            .all()
        )

        if not accounts:
            continue

        for account in accounts:

            # Platform matching
            platform_match = 100.0

            if campaign.target_platform:
                if (
                    account.platform.lower()
                    != campaign.target_platform.lower()
                ):
                    platform_match = 0.0

            # Follower matching
            metrics = (
                db.query(CreatorMetric)
                .filter(
                    CreatorMetric.account_id
                    == account.account_id
                )
                .order_by(
                    CreatorMetric.metric_date.asc()
                )
                .all()
            )

            if not metrics:
                continue

            latest = metrics[-1]

            follower_score = calculate_follower_score(
                followers=int(latest.followers),
                minimum=campaign.min_followers,
                maximum=campaign.max_followers
            )

            # Skip creators outside required follower range
            if follower_score == 0.0:
                continue

            # Niche matching
            niche_match = 100.0

            if campaign.target_niche:

                if creator.niche:

                    if (
                        creator.niche.lower()
                        != campaign.target_niche.lower()
                    ):
                        niche_match = 0.0

                else:
                    niche_match = 0.0

            # Country matching
            country_match = 100.0

            if campaign.target_country:

                if creator.country:

                    if (
                        creator.country.lower()
                        != campaign.target_country.lower()
                    ):
                        country_match = 0.0

                else:
                    country_match = 0.0

            # Growth calculations
            follower_growth = 0.0
            view_growth = 0.0

            if len(metrics) >= 2:

                previous = metrics[-2]

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

            # View ratio
            view_ratio = 0.0

            if latest.followers > 0:

                view_ratio = (
                    latest.avg_views
                    / latest.followers
                )

            # Performance score
            performance_score = (
                calculate_performance_score(
                    engagement_rate=float(
                        latest.engagement_rate
                    ),
                    average_views=int(
                        latest.avg_views
                    ),
                    follower_growth=follower_growth,
                    followers=int(
                        latest.followers
                    ),
                    view_ratio=view_ratio
                )
            )

            # Match score
            match_score = calculate_match_score(
                niche_match=niche_match,
                country_match=country_match,
                platform_match=platform_match,
                engagement_rate=float(
                    latest.engagement_rate
                ),
                performance_score=performance_score,
                follower_score=follower_score,
                view_growth=view_growth
            )

            # Recommendation reasons
            reasons = []

            if niche_match == 100.0:
                reasons.append(
                    "Strong niche match"
                )

            if country_match == 100.0:
                reasons.append(
                    "Target country match"
                )

            if platform_match == 100.0:
                reasons.append(
                    "Target platform match"
                )

            if float(latest.engagement_rate) >= 5:
                reasons.append(
                    "High engagement rate"
                )

            if follower_growth > 0:
                reasons.append(
                    "Positive follower growth"
                )

            if view_growth > 0:
                reasons.append(
                    "Positive view growth"
                )

            recommendations.append({
                "creator_id": creator.creator_id,
                "username": creator.username,
                "display_name": creator.display_name,
                "niche": creator.niche,
                "country": creator.country,
                "platform": account.platform,
                "followers": int(latest.followers),
                "average_views": int(latest.avg_views),
                "engagement_rate": float(
                    latest.engagement_rate
                ),
                "follower_growth": round(
                    follower_growth,
                    2
                ),
                "view_growth": round(
                    view_growth,
                    2
                ),
                "performance_score": performance_score,
                "match_score": match_score,
                "reasons": reasons
            })

    recommendations.sort(
        key=lambda creator: creator["match_score"],
        reverse=True
    )

    return recommendations
