"""Saved articles must work with catalog sizes above SQL Server's bind limit."""
import json
from types import SimpleNamespace
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from app.database.models import Base, Disease, Bookmark, User
from app.modules.library.icd_links import article_icd_links
from app.modules.profile.routes import bookmarks


def test_large_catalog_name_queries_are_bounded_and_links_preserved():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        for i in range(1200):
            db.add(Disease(slug=f'article-{i}', name=f'Bệnh {i}', english_name=f'Condition {i}',
                           category='Nhóm', summary='Tóm tắt', details='Chi tiết', risk_factors='',
                           prevention='', aliases=[], published=True))
        source = Disease(slug='imported-match', name='Bệnh 0', english_name='Condition 0',
                         category='ICD-11 14', summary='Condition 0',
                         details=json.dumps({'title':'Condition 0', 'class_kind':'category',
                                             'chapter_no':'14', 'code':'TEST', 'browser_url':'https://example.test'}),
                         risk_factors='', prevention='', aliases=[], published=False,
                         review_status='icd_classification')
        db.add(source)
        db.commit()
        parameter_counts = []
        def capture(connection, cursor, statement, parameters, context, executemany):
            parameter_counts.append(len(parameters))
        event.listen(engine, 'before_cursor_execute', capture)
        try:
            links = article_icd_links(db)
        finally:
            event.remove(engine, 'before_cursor_execute', capture)
        assert len(links) == 1
        assert next(iter(links.values()))['code'] == 'TEST'
        assert max(parameter_counts) <= 1001


def test_empty_saved_list_does_not_inspect_unrelated_catalog(monkeypatch):
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    def unexpected(*args):
        raise AssertionError('Empty bookmarks must not scan the entire catalog')
    monkeypatch.setattr('app.modules.profile.routes.article_icd_links', unexpected)
    with Session(engine) as db:
        assert bookmarks(db, SimpleNamespace(id=1)) == []


def test_saved_list_keeps_published_articles_private_to_owner():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        owner = User(email='owner@example.test', name='Owner', password_hash='test')
        row = Disease(slug='saved', name='Bài đã lưu', english_name='Saved article', category='Nhóm',
                      summary='Tóm tắt', details='Chi tiết', risk_factors='', prevention='', aliases=[], published=True)
        db.add_all([owner, row])
        db.flush()
        db.add(Bookmark(user_id=owner.id, disease_id=row.id))
        db.commit()
        assert [item['id'] for item in bookmarks(db, owner)] == [row.id]
        assert bookmarks(db, SimpleNamespace(id=owner.id + 1)) == []
        row.published = False
        db.commit()
        assert bookmarks(db, owner) == []
