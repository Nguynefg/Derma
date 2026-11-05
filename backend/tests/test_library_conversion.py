import gzip
import json
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from app.database.models import Base, Disease, MedicalDocument, DocumentVersion, User
from app.modules.library.library_source import source_data, source_filter
from app.modules.library.library_editorial import imported_form, save_editorial


def test_conversion_preserves_source_ids_and_is_restartable(tmp_path):
    from app.modules.library.library_conversion import convert_articles
    from app.modules.library.icd_routes import item
    engine = create_engine('sqlite:///' + (tmp_path / 'conversion.sqlite').as_posix())
    Base.metadata.create_all(engine)
    source = dict(title='Single episode depressive disorder', chapter_no='06',
        class_kind='category', linearization_uri='https://example.test/entity/1',
        browser_url='https://example.test/source', parent_uri=None, code='6A70')
    with Session(engine) as db, db.begin():
        row = Disease(slug='source-1', name='Old name', english_name=source['title'],
            category='ICD-11 06', summary=source['title'], details=json.dumps(source),
            risk_factors='', prevention='', aliases=['6A70'], review_status='icd_classification', published=False)
        db.add(row)
        db.flush()
        original_id = row.id
    result = convert_articles(engine, tmp_path / 'backups')
    assert result['converted'] == 1
    with gzip.open(result['backup'], 'rt', encoding='utf-8') as stream:
        backup = json.load(stream)
    assert backup[0]['disease_id'] == original_id
    assert json.loads(backup[0]['details']) == source
    with Session(engine) as db:
        row = db.get(Disease, original_id)
        assert row.slug == 'source-1'
        assert row.name == 'Rối loạn trầm cảm một giai đoạn'
        assert not row.details.startswith('{')
        assert 'ICD-11' not in row.category
        assert row.published is False  # No unreviewed clinical claims published.
        assert row.version == 2
        assert source_data(row) == source
        assert db.scalar(select(func.count()).select_from(MedicalDocument)) == 1
        assert db.scalar(select(func.count()).select_from(DocumentVersion)) == 1
        assert db.scalar(select(Disease.id).where(source_filter('chapter_no', '06'))) == original_id
        assert db.scalar(select(Disease.id).where(source_filter('class_kind', 'category'))) == original_id
        form = imported_form(row, db)
        for field in ['name','english_name','category','summary','details','risk_factors','prevention']:
            assert form[field] == getattr(row, field)
        assert item(row)['article_content']['details'] == row.details
    assert convert_articles(engine, tmp_path / 'backups')['converted'] == 0
    from app.core.schemas import DiseaseEdit
    from app.modules.library.icd_translation import apply_translated_titles
    with Session(engine) as db:
        admin = User(email='editor@example.test', name='Editor', password_hash='test-only', role='admin')
        db.add(admin)
        db.commit()
        body = DiseaseEdit(name='Tên đã được biên tập', english_name=source['title'],
            category='Sức khỏe tâm thần', summary='Tóm tắt đã được biên tập.',
            details='Nội dung tổng quan có nguồn để kiểm tra.', risk_factors='Yếu tố liên quan cần đối chiếu.',
            prevention='Thông tin chăm sóc cần đối chiếu.', published=False,
            symptom_ids=[], source_title='Tài liệu nguồn', source_url=source['browser_url'])
        save_editorial(db.get(Disease, original_id), body, db, admin)
        row = db.get(Disease, original_id)
        assert row.name == body.name and row.details == body.details
        assert source_data(row) == source
    apply_translated_titles(engine)
    with Session(engine) as db:
        assert db.get(Disease, original_id).name == 'Tên đã được biên tập'
    engine.dispose()
