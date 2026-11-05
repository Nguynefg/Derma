import hashlib
import json
from pathlib import Path
import sys
import pytest
from sqlalchemy import create_engine, select, update
from app.database.models import Base, Disease, DocumentVersion, Reference

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from scripts.content.apply_content_completion import apply_entries, validated, FIELDS


def setup():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(Disease.__table__.insert().values(slug='example', name='Bệnh thử', english_name='Example', category='Test', summary='', details='Giữ nguyên', risk_factors='', prevention='', aliases=[], published=False, review_status='icd_classification', version=2))
        row = dict(conn.execute(select(Disease.__table__)).mappings().one())
    source = {'url': 'https://medlineplus.gov/example.html', 'title': 'Example', 'text': 'This is an example condition.'}
    draft = {'id': str(row['disease_id']), **{f: {'text': '', 'evidence': []} for f in FIELDS}}
    draft['summary'] = {'text': 'Đây là bệnh thử.', 'evidence': [source['text']]}
    entry = {'draft': draft, 'source': source, 'source_sha256': hashlib.sha256(source['text'].encode()).hexdigest(), 'baseline': row, 'clinical_validation': False}
    return engine, entry


def test_apply_backup_provenance_and_idempotence(tmp_path):
    engine, entry = setup()
    result = apply_entries(engine, [entry], tmp_path / 'first', True)
    assert result['status'] == 'applied' and result['fields'] == 1
    assert Path(result['backup']).exists()
    with engine.connect() as conn:
        row = conn.execute(select(Disease.__table__)).mappings().one()
        assert row['summary'] == 'Đây là bệnh thử.' and row['details'] == 'Giữ nguyên'
        assert row['version'] == 3 and not row['published'] and row['review_status'] == 'icd_classification'
        assert json.loads(conn.scalar(select(DocumentVersion.content)))['source'] == entry['source']
        assert conn.scalar(select(Reference.url)) == entry['source']['url']
    assert apply_entries(engine, [entry], tmp_path / 'second', True)['records'] == 0


def test_conflict_changes_nothing(tmp_path):
    engine, entry = setup()
    with engine.begin() as conn:
        conn.execute(update(Disease).values(summary='Sửa thủ công'))
    assert apply_entries(engine, [entry], tmp_path, True)['status'] == 'conflicts_nothing_applied'
    with engine.connect() as conn:
        assert conn.scalar(select(Disease.summary)) == 'Sửa thủ công'
        assert conn.scalar(select(DocumentVersion.id)) is None


def test_missing_or_fabricated_evidence_rejected():
    _, entry = setup()
    entry['draft']['summary']['evidence'] = ['Not in the source']
    with pytest.raises(ValueError, match='Evidence'):
        validated(entry)


def test_populated_field_never_replaced():
    _, entry = setup()
    entry['baseline']['summary'] = 'Existing content'
    with pytest.raises(ValueError, match='populated'):
        validated(entry)


def test_preview_writes_neither_data_nor_backup(tmp_path):
    engine, entry = setup()
    assert apply_entries(engine, [entry], tmp_path, False)['status'] == 'preview'
    assert not list(tmp_path.glob('*.gz'))
    with engine.connect() as conn:
        assert conn.scalar(select(Disease.summary)) == ''
        assert conn.scalar(select(DocumentVersion.id)) is None


def test_conflict_in_second_record_blocks_the_whole_batch(tmp_path):
    import copy
    engine, entry = setup()
    second = copy.deepcopy(entry)
    second['draft']['id'] = '999999'
    result = apply_entries(engine, [entry, second], tmp_path, True)
    assert result['status'] == 'conflicts_nothing_applied'
    with engine.connect() as conn:
        assert conn.scalar(select(Disease.summary)) == ''
        assert conn.scalar(select(DocumentVersion.id)) is None


def test_changed_disease_name_blocks_source_application(tmp_path):
    engine, entry = setup()
    with engine.begin() as conn:
        conn.execute(update(Disease).values(name='Tên bệnh khác'))
    assert apply_entries(engine, [entry], tmp_path, True)['status'] == 'conflicts_nothing_applied'
    with engine.connect() as conn:
        assert conn.scalar(select(Disease.summary)) == ''


def test_drafting_requests_only_missing_field_and_discards_other_output(monkeypatch):
    import scripts.content.draft_medline_word_content as drafting
    captured = {}

    def response(instructions, parts, **kwargs):
        captured.update(json.loads(parts[0]['text'])[0])
        draft = {'id': '1', **{f: {'text': '', 'evidence': []} for f in FIELDS}}
        draft['summary'] = {'text': 'Unexpected replacement', 'evidence': ['Not a valid quote']}
        draft['prevention'] = {'text': 'Tái khám định kỳ.', 'evidence': ['Regular follow-up is important.']}
        return json.dumps({'items': [draft]})

    monkeypatch.setattr(drafting, 'generate', response)
    monkeypatch.setattr(drafting, 'REVIEW_DRAFTS', None)
    candidate = {'fields': {'disease_id': '1', 'name': 'Bệnh thử'}, 'missing': ['prevention'],
                 'source_title': 'Example', 'source': {'title': 'Example', 'text': 'Regular follow-up is important.'}}
    checked, rejected = drafting.request([candidate])
    assert not rejected
    assert captured['missing_fields'] == ['prevention']
    assert checked[0]['summary'] == {'text': '', 'evidence': []}
    assert checked[0]['prevention']['text'] == 'Tái khám định kỳ.'


def test_nci_attribution_translation_notice_and_license_are_preserved(tmp_path):
    engine, entry = setup()
    entry['source'].update(type='nci_thesaurus_definition',
                           url='https://ncit.nci.nih.gov/ncitbrowser/ConceptReport.jsp?code=C1',
                           license='CC BY 4.0', version='26.09d')
    result = apply_entries(engine, [entry], tmp_path, True)
    assert result['status'] == 'applied'
    with engine.connect() as conn:
        assert conn.scalar(select(Reference.publisher)) == 'National Cancer Institute'
        note = conn.scalar(select(Reference.usage_note))
        assert 'CC BY 4.0' in note and 'Adapted into Vietnamese' in note
        assert '26.09d' in note


def test_nci_source_without_license_is_rejected():
    _, entry = setup()
    entry['source'].update(type='nci_thesaurus_definition', url='https://ncit.nci.nih.gov/example')
    with pytest.raises(ValueError, match='license'):
        validated(entry)
