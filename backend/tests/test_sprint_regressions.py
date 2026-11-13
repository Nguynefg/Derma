"""Database-level regression checks, independent of the live SQL Server."""
import hashlib
import json

from sqlalchemy import create_engine, select, event
from sqlalchemy.orm import Session

from app.database.models import Base, Disease, Symptom, DiseaseSymptom, MedicalDocument, DocumentVersion, User
from app.core.schemas import DiseaseEdit, SymptomSearch
from app.modules.admin.routes import apply_edit
from app.modules.symptoms.routes import symptom_search


def test_article_edits_keep_private_versioned_snapshots():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        admin = User(email='admin@example.test', name='Admin', password_hash='test', role='admin')
        row = Disease(slug='revision-test', name='Tên', english_name='Name', category='Nhóm',
                      summary='Tóm tắt', details='Nội dung', risk_factors='', prevention='', aliases=[])
        db.add_all([admin, row])
        db.commit()
        body = DiseaseEdit(name='Tên mới', english_name='Name', category='Nhóm', summary='Tóm tắt bài viết',
                           details='Nội dung mới', risk_factors='Yếu tố', prevention='Phòng ngừa',
                           published=True, symptom_ids=[], source_title='Nguồn', source_url='https://example.test')
        apply_edit(row, body, db, admin, 'update')
        body.details = 'Lần sửa tiếp'
        apply_edit(row, body, db, admin, 'update')
        doc = db.scalar(select(MedicalDocument).where(MedicalDocument.slug == f'article-revision-{row.id}'))
        assert not doc.published
        versions = list(db.scalars(select(DocumentVersion).where(DocumentVersion.document_id == doc.id).order_by(DocumentVersion.version)))
        assert [v.version for v in versions] == [2, 3]
        assert json.loads(versions[0].content)['details'] == 'Nội dung mới'
        assert json.loads(versions[1].content)['details'] == 'Lần sửa tiếp'
        assert all(v.checksum == hashlib.sha256(v.content.encode()).hexdigest() for v in versions)


def test_symptom_search_queries_do_not_grow_per_article():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        symptom = Symptom(slug='itch', name='Ngứa')
        db.add(symptom)
        db.flush()
        for i in range(20):
            row = Disease(slug=f'lookup-{i}', name=f'Bệnh {i}', english_name='Name', category='Viêm da',
                          summary='Tóm tắt', details='Nội dung', risk_factors='', prevention='', aliases=[], published=True)
            db.add(row)
            db.flush()
            db.add(DiseaseSymptom(disease_id=row.id, symptom_id=symptom.id))
        db.commit()
        body = SymptomSearch(symptoms=[{'id': str(symptom.id), 'presence': 'present'}])
        statements = []
        def capture(connection, cursor, statement, *args):
            statements.append(statement)
        event.listen(engine, 'before_cursor_execute', capture)
        try:
            result = symptom_search(body, db)
        finally:
            event.remove(engine, 'before_cursor_execute', capture)
        assert len(result['items']) == 20
        assert all(item['match_count'] == 1 for item in result['items'])
        assert len(statements) < 12
