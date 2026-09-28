from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.sponsorship import Sponsorship
from app.models.creator import Creator
from app.models.campaign import Campaign

from schemas.sponsorship import (
    SponsorshipCreate,
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
    db: Session = Depends(get_db)
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

    if sponsorship.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="Invalid sponsorship status"
        )

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
        status=sponsorship.status,
        start_date=sponsorship.start_date,
        end_date=sponsorship.end_date
    )

    db.add(new_sponsorship)
    db.commit()
    db.refresh(new_sponsorship)

    return new_sponsorship


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
    db: Session = Depends(get_db)
):
    query = db.query(Sponsorship)
    if status:
        query = query.filter(Sponsorship.status == status)
    return query.all()


@router.get(
    "/{sponsorship_id}",
    response_model=SponsorshipResponse
)
def get_sponsorship(
    sponsorship_id: int,
    db: Session = Depends(get_db)
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

    return sponsorship


@router.patch(
    "/{sponsorship_id}/status",
    response_model=SponsorshipResponse
)
def update_sponsorship_status(
    sponsorship_id: int,
    status_update: SponsorshipStatusUpdate,
    db: Session = Depends(get_db)
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
    db: Session = Depends(get_db)
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

    return (
        db.query(Sponsorship)
        .filter(
            Sponsorship.campaign_id == campaign_id
        )
        .all()
    )
