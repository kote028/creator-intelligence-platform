from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.sponsorship import Sponsorship
from app.models.creator import Creator
from app.models.campaign import Campaign
from app.models.campaign_result import CampaignResult
from app.models.user import User
from app.auth_dependencies import get_current_user, require_brand, require_creator

from schemas.sponsorship import (
    SponsorshipCreate,
    CampaignApplicationCreate,
    CampaignResultUpsert,
    CampaignResultResponse,
    SponsorshipStatusUpdate,
    SponsorshipResponse
)


router = APIRouter(
    prefix="/sponsorships",
    tags=["Sponsorships"]
)


VALID_STATUSES = {
    "pending",
    "accepted",
    "rejected",
    "in_progress",
    "completed",
    "cancelled"
}


@router.post(
    "/",
    response_model=SponsorshipResponse
)
def create_sponsorship(
    sponsorship: SponsorshipCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_brand),
):

    creator = (
        db.query(Creator)
        .filter(
            Creator.creator_id
            == sponsorship.creator_id
        )
        .first()
    )

    if creator is None:
        raise HTTPException(
            status_code=404,
            detail="Creator not found"
        )

    campaign = (
        db.query(Campaign)
        .filter(
            Campaign.campaign_id
            == sponsorship.campaign_id
        )
        .first()
    )

    if campaign is None:
        raise HTTPException(
            status_code=404,
            detail="Campaign not found"
        )

    if current_user.brand is None or campaign.brand_id != current_user.brand.brand_id:
        raise HTTPException(status_code=403, detail="Only the campaign owner can send creator offers")

    if sponsorship.status != "pending":
        raise HTTPException(status_code=422, detail="New creator offers must start as pending")

    if sponsorship.agreed_amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Agreed amount must be greater than zero"
        )

    if sponsorship.agreed_amount > float(campaign.budget):
        raise HTTPException(
            status_code=400,
            detail="Agreed amount exceeds campaign budget"
        )

    existing = (
        db.query(Sponsorship)
        .filter(
            Sponsorship.creator_id
            == sponsorship.creator_id,
            Sponsorship.campaign_id
            == sponsorship.campaign_id
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Sponsorship already exists for this creator and campaign"
        )

    new_sponsorship = Sponsorship(
        creator_id=sponsorship.creator_id,
        campaign_id=sponsorship.campaign_id,
        agreed_amount=sponsorship.agreed_amount,
        initiated_by="brand",
        status="pending",
        start_date=sponsorship.start_date,
        end_date=sponsorship.end_date
    )

    db.add(new_sponsorship)
    db.commit()
    db.refresh(new_sponsorship)

    return new_sponsorship


@router.post("/applications", response_model=SponsorshipResponse, status_code=201)
def apply_to_campaign(
    application: CampaignApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_creator),
):
    creator = current_user.creator
    if creator is None:
        raise HTTPException(status_code=404, detail="Create your creator profile before applying")
    campaign = db.query(Campaign).filter(Campaign.campaign_id == application.campaign_id).first()
    if campaign is None or campaign.status != "active":
        raise HTTPException(status_code=404, detail="Active campaign not found")
    if campaign.end_date and campaign.end_date < date.today():
        raise HTTPException(status_code=409, detail="This campaign application period has ended")
    if application.agreed_amount > float(campaign.budget):
        raise HTTPException(status_code=422, detail="Your proposed rate exceeds the campaign budget")
    existing = db.query(Sponsorship).filter(
        Sponsorship.creator_id == creator.creator_id,
        Sponsorship.campaign_id == campaign.campaign_id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="You already applied to or received an offer for this campaign")
    record = Sponsorship(
        creator_id=creator.creator_id,
        campaign_id=campaign.campaign_id,
        agreed_amount=application.agreed_amount,
        status="pending",
        initiated_by="creator",
        application_message=application.application_message,
        start_date=application.start_date,
        end_date=application.end_date,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/{sponsorship_id}/results", response_model=CampaignResultResponse)
def get_campaign_results(
    sponsorship_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sponsorship = db.query(Sponsorship).filter(Sponsorship.sponsorship_id == sponsorship_id).first()
    if sponsorship is None:
        raise HTTPException(status_code=404, detail="Partnership not found")
    if not _is_party(sponsorship, current_user):
        raise HTTPException(status_code=403, detail="Partnership access required")
    if sponsorship.result is None:
        raise HTTPException(status_code=404, detail="No campaign results have been reported")
    return sponsorship.result


@router.put("/{sponsorship_id}/results", response_model=CampaignResultResponse)
def report_campaign_results(
    sponsorship_id: int,
    result_data: CampaignResultUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_brand),
):
    sponsorship = db.query(Sponsorship).filter(Sponsorship.sponsorship_id == sponsorship_id).first()
    if sponsorship is None:
        raise HTTPException(status_code=404, detail="Partnership not found")
    if current_user.brand is None or sponsorship.campaign.brand_id != current_user.brand.brand_id:
        raise HTTPException(status_code=403, detail="Only the campaign owner can report outcomes")
    if sponsorship.status not in {"accepted", "in_progress", "completed"}:
        raise HTTPException(status_code=409, detail="Report outcomes after accepting the partnership")

    result = sponsorship.result
    if result is None:
        result = CampaignResult(sponsorship_id=sponsorship.sponsorship_id)
        db.add(result)
    for field, value in result_data.model_dump().items():
        setattr(result, field, value)
    db.commit()
    db.refresh(result)
    return result


ALLOWED_TRANSITIONS = {
    "pending": {"accepted", "rejected", "cancelled"},
    "accepted": {"in_progress", "cancelled"},
    "in_progress": {"completed", "cancelled"},
    "rejected": set(),
    "completed": set(),
    "cancelled": set()
}


@router.get(
    "/",
    response_model=list[SponsorshipResponse]
)
def get_sponsorships(
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Sponsorship).join(Campaign).join(Creator)
    if current_user.role == "brand":
        if current_user.brand is None:
            return []
        query = query.filter(Campaign.brand_id == current_user.brand.brand_id)
    elif current_user.role == "creator":
        if current_user.creator is None:
            return []
        query = query.filter(Sponsorship.creator_id == current_user.creator.creator_id)
    else:
        raise HTTPException(status_code=403, detail="Marketplace account access required")
    if status:
        query = query.filter(Sponsorship.status == status)
    return query.all()


@router.get(
    "/{sponsorship_id}",
    response_model=SponsorshipResponse
)
def get_sponsorship(
    sponsorship_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    sponsorship = (
        db.query(Sponsorship)
        .filter(
            Sponsorship.sponsorship_id
            == sponsorship_id
        )
        .first()
    )

    if sponsorship is None:
        raise HTTPException(
            status_code=404,
            detail="Sponsorship not found"
        )

    if not _is_party(sponsorship, current_user):
        raise HTTPException(status_code=403, detail="Partnership access required")

    return sponsorship


@router.patch(
    "/{sponsorship_id}/status",
    response_model=SponsorshipResponse
)
def update_sponsorship_status(
    sponsorship_id: int,
    status_update: SponsorshipStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    sponsorship = (
        db.query(Sponsorship)
        .filter(
            Sponsorship.sponsorship_id
            == sponsorship_id
        )
        .first()
    )

    if sponsorship is None:
        raise HTTPException(
            status_code=404,
            detail="Sponsorship not found"
        )

    _authorize_status_change(sponsorship, current_user, status_update.status)

    if status_update.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="Invalid sponsorship status"
        )

    allowed = ALLOWED_TRANSITIONS.get(sponsorship.status, set())
    if status_update.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cannot transition status from '{sponsorship.status}' to '{status_update.status}'. "
                f"Allowed transitions: {sorted(list(allowed)) or 'None (terminal state)'}"
            )
        )

    sponsorship.status = status_update.status

    db.commit()
    db.refresh(sponsorship)

    return sponsorship


@router.delete("/{sponsorship_id}")
def delete_sponsorship(
    sponsorship_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sponsorship = (
        db.query(Sponsorship)
        .filter(
            Sponsorship.sponsorship_id
            == sponsorship_id
        )
        .first()
    )

    if sponsorship is None:
        raise HTTPException(
            status_code=404,
            detail="Sponsorship not found"
        )

    if not _is_party(sponsorship, current_user) or sponsorship.status != "pending":
        raise HTTPException(status_code=403, detail="Only a pending partnership participant can remove an offer")

    db.delete(sponsorship)
    db.commit()

    return {
        "message": f"Sponsorship {sponsorship_id} successfully deleted"
    }


@router.get(
    "/creator/{creator_id}",
    response_model=list[SponsorshipResponse]
)
def get_creator_sponsorships(
    creator_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

    if current_user.role != "creator" or current_user.creator is None or current_user.creator.creator_id != creator_id:
        raise HTTPException(status_code=403, detail="Creator account access required")

    return (
        db.query(Sponsorship)
        .filter(
            Sponsorship.creator_id == creator_id
        )
        .all()
    )


@router.get(
    "/campaign/{campaign_id}",
    response_model=list[SponsorshipResponse]
)
def get_campaign_sponsorships(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_brand),
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

    if current_user.brand is None or current_user.brand.brand_id != campaign.brand_id:
        raise HTTPException(status_code=403, detail="Brand account access required")

    return (
        db.query(Sponsorship)
        .filter(
            Sponsorship.campaign_id == campaign_id
        )
        .all()
    )


def _is_party(sponsorship: Sponsorship, user: User) -> bool:
    if user.role == "brand":
        return bool(user.brand and sponsorship.campaign.brand_id == user.brand.brand_id)
    if user.role == "creator":
        return bool(user.creator and sponsorship.creator_id == user.creator.creator_id)
    return False


def _authorize_status_change(sponsorship: Sponsorship, user: User, new_status: str) -> None:
    if not _is_party(sponsorship, user):
        raise HTTPException(status_code=403, detail="Partnership access required")
    if user.role == "brand":
        allowed = {"in_progress", "completed", "cancelled"}
        if sponsorship.status == "pending" and sponsorship.initiated_by == "creator":
            allowed = {"accepted", "rejected"}
        if new_status not in allowed:
            raise HTTPException(status_code=403, detail="Brand cannot make this partnership status change")
    elif user.role == "creator":
        allowed = {"cancelled", "completed"}
        if sponsorship.status == "pending" and sponsorship.initiated_by == "brand":
            allowed = {"accepted", "rejected"}
        if new_status not in allowed:
            raise HTTPException(status_code=403, detail="Creator cannot make this partnership status change")
