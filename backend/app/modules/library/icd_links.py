from app.modules.library.library_source import source_data, source_filter, preload_sources
"""Conservative, reversible article/ICD associations; source rows remain intact."""

import json
from collections import defaultdict
from sqlalchemy import select, func, or_
from sqlalchemy.orm import load_only
from app.database.connection import Disease
from app.modules.library.icd_translation import translated_title


def article_icd_links(db):
    articles = db.scalars(
        select(Disease).options(load_only(Disease.id, Disease.name, Disease.english_name, Disease.aliases, Disease.details)).where(
            Disease.published == True, Disease.review_status != "icd_classification"
        )
    ).all()
    by_name = defaultdict(list)
    for article in articles:
        if article.english_name.strip():
            by_name[article.english_name.strip().lower()].append(article.id)
    if not by_name:
        return {}
    # A large library exceeds SQL Server's parameter budget if every name is
    # placed into both IN clauses at once. Deduplicate rows across batches:
    # different full names can share the same truncated English title.
    names = list(by_name)
    candidates_by_id = {}
    for offset in range(0, len(names), 500):
        batch = names[offset:offset + 500]
        for row in db.scalars(
            select(Disease).options(load_only(Disease.id, Disease.aliases, Disease.details)).where(
                Disease.review_status == "icd_classification",
                or_(func.lower(Disease.english_name).in_(list(dict.fromkeys(n[:120] for n in batch))),
                    func.lower(Disease.summary).in_(batch)),
            )
        ):
            candidates_by_id[row.id] = row
    candidates = list(candidates_by_id.values())
    matches = defaultdict(list)
    retained = [a for a in articles if any(alias.startswith('merged-id:') for alias in (a.aliases or []))]
    preload_sources(db, retained)
    for article in retained:
        data = source_data(article)
        if data.get('class_kind') != 'category' or by_name.get(data.get('title','').strip().lower()) != [article.id]:
            continue
        old_ids = [int(a[10:]) for a in article.aliases if a.startswith('merged-id:') and a[10:].isdigit()]
        if len(old_ids) == 1:
            matches[article.id].append({'id':old_ids[0],'title':article.name,
                'original_title':data['title'],'code':data.get('code'),
                'chapter':data.get('chapter_no',''),'source_url':data.get('browser_url','')})
    preload_sources(db, candidates)
    for row in candidates:
        data = source_data(row)
        name = data.get("title", "").strip().lower()
        # Never merge blocks, chapters, approximate names or ambiguous matches.
        if data.get("class_kind") != "category" or len(by_name.get(name, [])) != 1:
            continue
        matches[by_name[name][0]].append(
            {
                "id": row.id,
                "title": translated_title(row, data["title"]),
                "original_title": data["title"],
                "code": data.get("code"),
                "chapter": data.get("chapter_no", ""),
                "source_url": data.get("browser_url", ""),
            }
        )
    return {article_id: rows[0] for article_id, rows in matches.items() if len(rows) == 1}
