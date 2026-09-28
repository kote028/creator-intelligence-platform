from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User

from app.auth import (
    hash_password,
    verify_password,
    create_access_token
)

from schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse
)

from app.auth_dependencies import(
 get_current_user,
 require_creator,
 require_brand
)
from app.models.user import User


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


VALID_ROLES = {
    "creator",
    "brand"
}


@router.post(
    "/register",
    response_model=TokenResponse
)
def register(
    user_data: RegisterRequest,
    db: Session = Depends(get_db)
):

    if user_data.role not in VALID_ROLES:

        raise HTTPException(
            status_code=400,
            detail="Invalid role"
        )

    existing_user = (
        db.query(User)
        .filter(
            User.email == user_data.email
        )
        .first()
    )

    if existing_user:

        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    if len(user_data.password) < 8:

        raise HTTPException(
            status_code=400,
            detail="Password must contain at least 8 characters"
        )

    hashed_password = hash_password(
        user_data.password
    )

    new_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        role=user_data.role
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = create_access_token({
        "sub": str(new_user.user_id),
        "role": new_user.role
    })

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": new_user.user_id,
        "role": new_user.role
    }


@router.post(
    "/login",
    response_model=TokenResponse
)
def login(
    user_data: LoginRequest,
    db: Session = Depends(get_db)
):

    user = (
        db.query(User)
        .filter(
            User.email == user_data.email
        )
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not verify_password(
        user_data.password,
        user.password_hash
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    access_token = create_access_token({
        "sub": str(user.user_id),
        "role": user.role
    })

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.user_id,
        "role": user.role
    }

@router.get("/me")
def get_me(
    current_user: User = Depends(get_current_user)
):
    return {
        "user_id": current_user.user_id,
        "email": current_user.email,
        "role": current_user.role,
        "creator_id": current_user.creator.creator_id if current_user.creator else None,
        "brand_id": current_user.brand.brand_id if current_user.brand else None
    }


@router.get("/creator-only")
def creator_only(
    current_user: User = Depends(require_creator)
):
    return {
        "message": "You have creator access",
        "user_id": current_user.user_id
    }


@router.get("/brand-only")
def brand_only(
    current_user: User = Depends(require_brand)
):
    return {
        "message": "You have brand access",
        "user_id": current_user.user_id
    }
