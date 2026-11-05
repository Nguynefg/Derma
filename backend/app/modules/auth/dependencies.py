"""Session, CSRF and role dependencies; shared by routes."""

import secrets
from datetime import timedelta, timezone
from fastapi import Depends, HTTPException, Request
from app.modules.library.identifiers import find_record
from sqlalchemy import delete
from sqlalchemy.orm import Session
from app.database.connection import get_db, now, User, LoginSession
from app.core.config import COOKIE, SECURE_COOKIE
from app.core.security import digest


def current_session(request: Request, db: Session):
    token = request.cookies.get(COOKIE)
    row = db.get(LoginSession, digest(token)) if token else None
    if row:
        expiry = (
            row.expires_at.replace(tzinfo=timezone.utc)
            if row.expires_at.tzinfo is None
            else row.expires_at
        )
        if expiry <= now():
            db.delete(row)
            db.commit()
            row = None
    if not row:
        raise HTTPException(401, "Vui lòng đăng nhập để tiếp tục.")
    return row


def get_user(request: Request, db: Session = Depends(get_db)):
    session = current_session(request, db)
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        if not secrets.compare_digest(request.headers.get("x-csrf-token", ""), session.csrf):
            raise HTTPException(403, "Phiên làm việc không hợp lệ. Vui lòng tải lại trang.")
    user = find_record(db, User, session.user_id)
    if not user:
        raise HTTPException(401, "Phiên làm việc đã hết hạn.")
    return user


def get_admin(user: User = Depends(get_user)):
    if user.role != "admin":
        raise HTTPException(403, "Bạn không có quyền quản trị.")
    return user


def public_user(user):
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}


def start_session(user, db, response, request):
    old_token = request.cookies.get(COOKIE)
    if old_token:
        db.execute(delete(LoginSession).where(LoginSession.token_hash == digest(old_token)))
    db.execute(delete(LoginSession).where(LoginSession.expires_at < now()))
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    db.add(
        LoginSession(
            token_hash=digest(token),
            user_id=user.id,
            csrf=csrf,
            expires_at=now() + timedelta(hours=12),
        )
    )
    db.commit()
    response.set_cookie(
        COOKIE, token, httponly=True, secure=SECURE_COOKIE, samesite="lax", max_age=43200, path="/"
    )
    return {"user": public_user(user), "csrf": csrf}
