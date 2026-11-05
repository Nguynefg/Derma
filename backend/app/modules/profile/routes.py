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


class ProfileEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=80)


class PasswordEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


@router.patch("/api/v1/auth/profile")
def edit_profile(body: ProfileEdit, db: Session = Depends(get_db), user: User = Depends(get_user)):
    name = body.name.strip()
    if not name:
        raise HTTPException(422, "Vui lòng nhập tên của bạn.")
    user.name = name
    db.commit()
    return {"user": public_user(user)}


@router.post("/api/v1/auth/password")
def change_password(
    body: PasswordEdit,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_user),
):
    rate_limit(request, "password", 5)
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(400, "Mật khẩu hiện tại không đúng.")
    if not valid_new_password(body.new_password):
        raise HTTPException(422, PASSWORD_REQUIREMENT)
    if body.new_password == body.current_password:
        raise HTTPException(422, "Mật khẩu mới phải khác mật khẩu hiện tại.")
    user.password_hash = hash_password(body.new_password)
    db.execute(delete(LoginSession).where(LoginSession.user_id == user.id))
    # Rotate this browser's cookie and CSRF; all other sessions stay revoked.
    return start_session(user, db, response, request)


@router.get("/api/v1/bookmarks")
def bookmarks(db: Session = Depends(get_db), user: User = Depends(get_user)):
    rows = db.scalars(
        select(Disease)
        .join(Bookmark, Bookmark.disease_id == Disease.id)
        .where(Bookmark.user_id == user.id, Disease.published == True)
        .order_by(Bookmark.created_at.desc(), Disease.id)
    )
    links = article_icd_links(db)
    return [serialize_disease(row, db, links) for row in rows]


@router.put("/api/v1/bookmarks/{disease_id}", status_code=204)
def save_bookmark(disease_id: int, db: Session = Depends(get_db), user: User = Depends(get_user)):
    disease = db.get(Disease, disease_id)
    if not disease or not disease.published:
        raise HTTPException(404, "Không tìm thấy bài viết.")
    if not db.get(Bookmark, (user.id, disease_id)):
        db.add(Bookmark(user_id=user.id, disease_id=disease_id))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            if not db.get(Bookmark, (user.id, disease_id)):
                raise


@router.delete("/api/v1/bookmarks/{disease_id}", status_code=204)
def remove_bookmark(disease_id: int, db: Session = Depends(get_db), user: User = Depends(get_user)):
    db.execute(
        delete(Bookmark).where(Bookmark.user_id == user.id, Bookmark.disease_id == disease_id)
    )
    db.commit()


