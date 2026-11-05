import importlib.util
from pathlib import Path
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location('word_sync', Path(__file__).resolve().parents[2]/'scripts/import_export/sync_word_database.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def example():
    before = dict.fromkeys(module.KEYS, 'unchanged')
    before.update(slug='example', aliases=['old'], summary='original')
    after = dict(before, summary='updated', aliases=['old','new'])
    live = SimpleNamespace(**before)
    return before, after, live

def test_merge_preserves_live_aliases_and_detects_live_content_edits():
    before, after, live = example()
    live.aliases=['old','admin-added']
    live.summary='admin edit'
    changes, conflicts=module.plan(before,after,live)
    assert conflicts==['summary']
    assert changes=={'aliases':['old','admin-added','new']}

def test_repeat_import_is_idempotent():
    before, after, live=example()
    live.summary=after['summary']
    live.aliases=after['aliases']
    assert module.plan(before,after,live)==({},[])

def test_matching_baseline_applies_content_and_rejects_wrong_slug():
    before, after, live=example()
    assert module.plan(before,after,live)[0]['summary']=='updated'
    live.slug='another-record'
    assert module.plan(before,after,live)==({},['slug'])
