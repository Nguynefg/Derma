"""Sort/page narrow keys before fetching large article text columns."""
from sqlalchemy import select
from app.database.models import Disease


def article_page(db, query, ordering, page, page_size):
    ids = list(db.scalars(
        query.with_only_columns(Disease.id, maintain_column_froms=True)
        .order_by(*ordering).offset((page - 1) * page_size).limit(page_size)
    ))
    if not ids:
        return []
    rows = {row.id: row for row in db.scalars(select(Disease).where(Disease.id.in_(ids)))}
    return [rows[record_id] for record_id in ids if record_id in rows]
