"""Auth HTTP endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.database.connection import get_db, User, LoginSession
from app.core.config import COOKIE
from app.core.security import hash_password, verify_password, digest, rate_limit
from app.core.schemas import Credentials
from app.core.password_policy import valid_new_password, PASSWORD_REQUIREMENT
from app.modules.auth.dependencies import get_user, current_session, public_user, start_session
from pydantic import BaseModel, Field, ConfigDict
from app.database.models import Bookmark, Disease
from app.modules.library.catalog import serialize_disease
from app.modules.library.icd_links import article_icd_links

router = APIRouter()


@router.post("/api/v1/auth/register", status_code=201)
def register(
    body: Credentials, request: Request, response: Response, db: Session = Depends(get_db)
):
    rate_limit(request, "auth", 15)
    if not valid_new_password(body.password):
        raise HTTPException(422, PASSWORD_REQUIREMENT)
    user = User(
        email=body.email,
        name=body.name.strip() or "Bạn đọc",
        password_hash=hash_password(body.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409, "Không thể đăng ký bằng email này. Hãy đăng nhập nếu đã có tài khoản."
        )
    return start_session(user, db, response, request)


@router.post("/api/v1/auth/login")
def login(body: Credentials, request: Request, response: Response, db: Session = Depends(get_db)):
    rate_limit(request, "auth", 15)
    user = db.scalar(select(User).where(User.email == body.email))
    # Perform the same expensive KDF even for unknown accounts.
    valid = (
        verify_password(body.password, user.password_hash)
        if user
        else verify_password(body.password, "scrypt$dummy$" + "0" * 128)
    )
    if not user or not valid:
        raise HTTPException(401, "Email hoặc mật khẩu không đúng.")
    return start_session(user, db, response, request)


@router.get("/api/v1/auth/me")
def me(request: Request, db: Session = Depends(get_db), user: User = Depends(get_user)):
    return {"user": public_user(user), "csrf": current_session(request, db).csrf}


@router.post("/api/v1/auth/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_user),
):
    db.execute(
        delete(LoginSession).where(LoginSession.token_hash == digest(request.cookies[COOKIE]))
    )
    db.commit()
    response.delete_cookie(COOKIE, path="/")
