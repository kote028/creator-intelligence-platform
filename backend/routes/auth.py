import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import create_access_token, hash_password, verify_password
from app.auth_dependencies import get_current_user, require_brand, require_creator
from app.config import GOOGLE_CLIENT_ID
from app.database import get_db
from app.google_oauth import (
    GoogleCredentialError,
    GoogleProviderUnavailable,
    verify_google_credential,
)
from app.models.user import User
from schemas.auth import (
    AuthCredentials,
    GoogleCredentialRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
VALID_ROLES = {"creator", "brand"}


def _token_response(user: User) -> dict:
    return {
        "access_token": create_access_token({"sub": str(user.user_id), "role": user.role}),
        "token_type": "bearer",
        "user_id": user.user_id,
        "email": user.email,
        "role": user.role,
        "creator_id": user.creator.creator_id if user.creator else None,
        "brand_id": user.brand.brand_id if user.brand else None,
        "google_linked": bool(user.google_subject),
    }


def _register(email: str, password: str, role: str, db: Session) -> dict:
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    try:
        user = User(email=email, password_hash=hash_password(password), role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered") from error
    return _token_response(user)


def _login(email: str, password: str, expected_role: str | None, db: Session) -> dict:
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if expected_role and user.role != expected_role:
        raise HTTPException(status_code=403, detail="Use the sign-in page for your account type")
    return _token_response(user)


def _google_sign_in(credential: str, role: str, db: Session) -> dict:
    try:
        claims = verify_google_credential(credential)
    except GoogleCredentialError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error
    except GoogleProviderUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    subject = claims["sub"]
    email = claims["email"].strip().lower()
    user = db.query(User).filter(User.google_subject == subject).first()
    if user:
        if user.role != role:
            raise HTTPException(status_code=403, detail="Use the sign-in page for your account type")
        return _token_response(user)
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(
            status_code=409,
            detail="An account already uses this email. Sign in with your password, then connect Google from your profile.",
        )

    try:
        user = User(
            email=email,
            password_hash=hash_password(secrets.token_urlsafe(48)),
            role=role,
            google_subject=subject,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="This Google account is already linked") from error
    return _token_response(user)


@router.post("/register", response_model=TokenResponse)
def register(user_data: RegisterRequest, db: Session = Depends(get_db)):
    if user_data.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    return _register(user_data.email, user_data.password, user_data.role, db)


@router.post("/login", response_model=TokenResponse)
def login(user_data: LoginRequest, db: Session = Depends(get_db)):
    return _login(user_data.email, user_data.password, None, db)


@router.post("/creator/register", response_model=TokenResponse, status_code=201)
def register_creator(data: AuthCredentials, db: Session = Depends(get_db)):
    return _register(data.email, data.password, "creator", db)


@router.post("/company/register", response_model=TokenResponse, status_code=201)
def register_company(data: AuthCredentials, db: Session = Depends(get_db)):
    return _register(data.email, data.password, "brand", db)


@router.post("/creator/login", response_model=TokenResponse)
def login_creator(data: LoginRequest, db: Session = Depends(get_db)):
    return _login(data.email, data.password, "creator", db)


@router.post("/company/login", response_model=TokenResponse)
def login_company(data: LoginRequest, db: Session = Depends(get_db)):
    return _login(data.email, data.password, "brand", db)


@router.get("/oauth/google/config")
def google_oauth_config():
    return {"client_id": GOOGLE_CLIENT_ID}


@router.post("/creator/google", response_model=TokenResponse)
def creator_google_sign_in(data: GoogleCredentialRequest, db: Session = Depends(get_db)):
    return _google_sign_in(data.credential, "creator", db)


@router.post("/company/google", response_model=TokenResponse)
def company_google_sign_in(data: GoogleCredentialRequest, db: Session = Depends(get_db)):
    return _google_sign_in(data.credential, "brand", db)


@router.post("/google/link")
def link_google_account(
    data: GoogleCredentialRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        claims = verify_google_credential(data.credential)
    except GoogleCredentialError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error
    except GoogleProviderUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    if claims["email"].strip().lower() != current_user.email.lower():
        raise HTTPException(status_code=403, detail="Google account email must match your marketplace account")
    existing = db.query(User).filter(User.google_subject == claims["sub"]).first()
    if existing and existing.user_id != current_user.user_id:
        raise HTTPException(status_code=409, detail="This Google account is linked to another user")
    current_user.google_subject = claims["sub"]
    db.commit()
    return {"message": "Google account linked"}


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "user_id": current_user.user_id,
        "email": current_user.email,
        "role": current_user.role,
        "creator_id": current_user.creator.creator_id if current_user.creator else None,
        "brand_id": current_user.brand.brand_id if current_user.brand else None,
        "google_linked": bool(current_user.google_subject),
    }


@router.get("/creator-only")
def creator_only(current_user: User = Depends(require_creator)):
    return {"message": "You have creator access", "user_id": current_user.user_id}


@router.get("/brand-only")
def brand_only(current_user: User = Depends(require_brand)):
    return {"message": "You have brand access", "user_id": current_user.user_id}
