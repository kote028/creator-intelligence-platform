from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.brand import Brand
from app.models.user import User
from app.auth_dependencies import get_current_user, require_brand

from schemas.brand import BrandCreate, BrandUpdate, BrandResponse


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


@router.get("/me", response_model=BrandResponse)
def get_my_brand_profile(
    current_user: User = Depends(require_brand),
    db: Session = Depends(get_db)
):
    if not current_user.brand:
        raise HTTPException(
            status_code=404,
            detail="Brand profile not found for this account"
        )
    return current_user.brand


@router.put("/me", response_model=BrandResponse)
def update_my_brand_profile(
    update_data: BrandUpdate,
    current_user: User = Depends(require_brand),
    db: Session = Depends(get_db)
):
    brand = current_user.brand
    if not brand:
        raise HTTPException(
            status_code=404,
            detail="Brand profile not found for this account"
        )
    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(brand, field, value)
    db.commit()
    db.refresh(brand)
    return brand


@router.post("/me", response_model=BrandResponse)
def create_my_brand_profile(
    brand: BrandCreate,
    current_user: User = Depends(require_brand),
    db: Session = Depends(get_db)
):
    if current_user.brand:
        raise HTTPException(
            status_code=400,
            detail="Brand profile already exists for this account"
        )
    existing = db.query(Brand).filter(Brand.email == brand.email).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Brand with this email already exists"
        )
    new_brand = Brand(
        user_id=current_user.user_id,
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


@router.put(
    "/{brand_id}",
    response_model=BrandResponse
)
def update_brand(
    brand_id: int,
    brand_update: BrandUpdate,
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

    for field, value in brand_update.model_dump(exclude_unset=True).items():
        setattr(brand, field, value)

    db.commit()
    db.refresh(brand)

    return brand


@router.delete("/{brand_id}")
def delete_brand(
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

    db.delete(brand)
    db.commit()

    return {
        "message": f"Brand {brand_id} successfully deleted"
    }
