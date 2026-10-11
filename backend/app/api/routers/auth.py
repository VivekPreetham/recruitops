from fastapi import Depends, APIRouter, Cookie, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.errors import UnauthorizedError
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import (
    CandidateRegister,
    LoginRequest,
    RecruiterRegister,
    TokenResponse,
    UserOut,
) 
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_NAME = "refresh_token"
COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(
    response: Response,
    token: str
) -> None:
    s = get_settings()
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        secure=s.cookie_secure,
        samesite="lax",
        max_age=s.jwt_refresh_ttl_days * 86400,
        path=COOKIE_PATH,
    )


@router.post("/register/recruiter", response_model=UserOut, status_code=201)
def register_recruiter(body: RecruiterRegister, db: Session = Depends(get_db)):
    return auth_service.register_recruiter(db, **body.model_dump())

@router.post("/register/candidate", response_model=UserOut, status_code=201)
def register_candidate(body: CandidateRegister, db: Session = Depends(get_db)):
    return auth_service.register_candidate(db, **body.model_dump())

@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    access, refresh = auth_service.login(db, email=body.email, password=body.password)
    _set_refresh_cookie(response, refresh)
    return TokenResponse(access_token=access)

@router.post("/refresh", response_model=TokenResponse)
def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    if not refresh_token:
        raise UnauthorizedError("Missing refresh token")
    access, new_refresh = auth_service.refresh(db, raw_token=refresh_token)
    _set_refresh_cookie(response, new_refresh)
    return TokenResponse(access_token=access)

@router.post("/logout", status_code=204)
def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    auth_service.logout(db, raw_token=refresh_token)
    response.delete_cookie(COOKIE_NAME, path=COOKIE_PATH)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user