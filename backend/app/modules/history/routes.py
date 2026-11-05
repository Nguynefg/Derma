"""History HTTP endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from app.modules.library.identifiers import find_record
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from app.database.connection import get_db, User, Disease, History
from app.core.schemas import SaveHistory
from app.modules.auth.dependencies import get_user

router = APIRouter()


@router.post("/api/v1/history", status_code=201)
def save_history(body: SaveHistory, db: Session = Depends(get_db), user: User = Depends(get_user)):
    if not body.consent:
        raise HTTPException(422, "Cần đồng ý trước khi lưu lịch sử.")
    results = []
    for item in dict.fromkeys(body.result_ids):
        row = find_record(db, Disease, item)
        if not row or not row.published:
            raise HTTPException(422, "Kết quả không hợp lệ.")
        results.append({"id": row.id, "name": row.name, "version": row.version})
    row = History(user_id=user.id, mode=body.mode, query=body.query, results=results)
    db.add(row)
    db.commit()
    return {"id": row.id}


@router.get("/api/v1/history")
def history(db: Session = Depends(get_db), user: User = Depends(get_user)):
    rows = db.scalars(
        select(History)
        .where(History.user_id == user.id)
        .order_by(History.created_at.desc())
        .limit(100)
    )
    return [
        {
            "id": r.id,
            "mode": r.mode,
            "query": r.query,
            "results": r.results,
            "created_at": r.created_at.isoformat(),
            "consent_version": r.consent_version,
        }
        for r in rows
    ]


@router.delete("/api/v1/history", status_code=204)
def clear_history(db: Session = Depends(get_db), user: User = Depends(get_user)):
    db.execute(delete(History).where(History.user_id == user.id))
    db.commit()


@router.delete("/api/v1/history/{history_id}", status_code=204)
def remove_history(history_id: str, db: Session = Depends(get_db), user: User = Depends(get_user)):
    row = find_record(db, History, history_id)
    if not row or row.user_id != user.id:
        raise HTTPException(404, "Không tìm thấy mục lịch sử.")
    db.delete(row)
    db.commit()
