from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.brand import Brand

from schemas.brand import BrandCreate, BrandResponse


router = APIRouter(
    prefix="/brands",
    tags=["Brands"]
)


@router.post(
    "/",
    response_model=BrandResponse
)
def create_brand(
    brand: BrandCreate,
    db: Session = Depends(get_db)
):
    existing_brand = (
        db.query(Brand)
        .filter(Brand.email == brand.email)
        .first()
    )

    if existing_brand:
        raise HTTPException(
            status_code=400,
            detail="Brand with this email already exists"
        )

    new_brand = Brand(
        company_name=brand.company_name,
        email=brand.email,
        website=brand.website,
        industry=brand.industry
    )

    db.add(new_brand)
    db.commit()
    db.refresh(new_brand)

    return new_brand


@router.get(
    "/",
    response_model=list[BrandResponse]
)
def get_brands(
    db: Session = Depends(get_db)
):
    return db.query(Brand).all()


@router.get(
    "/{brand_id}",
    response_model=BrandResponse
)
def get_brand(
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

    return brand
