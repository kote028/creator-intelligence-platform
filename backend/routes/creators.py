from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.creator import Creator
from schemas.creator import CreatorCreate, CreatorResponse


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
