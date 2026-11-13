import json
from pathlib import Path
import sys
sys.path.insert(0, 'f:/App/Codex/derma-library/backend')

from app.data import seed, library_expansion, library_extended, library_dermnet, library_general

covers_file = Path('f:/App/Codex/derma-library/frontend/src/shared/data/diseaseCovers.json')
with open(covers_file, encoding='utf-8') as f:
    covers = json.load(f)

public_dir = Path('f:/App/Codex/derma-library/frontend/public')

cover_map = {}
for c in covers:
    for n in c.get('names', []):
        norm = n.strip().lower()
        cover_map[norm] = c

datasets = [
    ('seed', seed.DATA),
    ('expansion', library_expansion.DATA),
    ('extended', library_extended.DATA),
    ('dermnet', library_dermnet.DATA),
    ('general', library_general.DATA),
]

all_diseases = []
seen = set()
for source, dataset in datasets:
    for item in dataset:
        name = item.get('name', '').strip()
        eng = item.get('english_name', '').strip()
        slug = item.get('id') or item.get('slug') or name
        if name and name not in seen:
            seen.add(name)
            all_diseases.append({'name': name, 'english_name': eng, 'slug': slug, 'source': source, 'category': item.get('category', '')})

missing = []
has_cover = []

for d in all_diseases:
    eng_norm = d['english_name'].lower().strip()
    vn_norm = d['name'].lower().strip()
    cover = cover_map.get(eng_norm) or cover_map.get(vn_norm)
    if not cover:
        missing.append((d, 'Chưa có mục trong diseaseCovers.json'))
    else:
        src = cover.get('src', '').lstrip('/')
        file_path = public_dir / src
        if not file_path.exists():
            missing.append((d, f'File ảnh không tồn tại: {src}'))
        else:
            has_cover.append((d, str(src)))

print(f"Tổng số bệnh lý trong hệ thống: {len(all_diseases)}")
print(f"Bệnh ĐÃ CÓ ảnh bìa hợp lệ: {len(has_cover)}")
print(f"Bệnh ĐANG THIẾU ảnh bìa: {len(missing)}")

print("\n--- DANH SÁCH BỆNH ĐANG THIẾU ẢNH ---")
for idx, (d, reason) in enumerate(missing, 1):
    print(f"{idx}. {d['name']} ({d['english_name']}) - Nhóm: {d['category']} [{d['source']}]")

with open('f:/App/Codex/derma-library/docs/missing_diseases.json', 'w', encoding='utf-8') as f:
    json.dump([{'name': d['name'], 'english_name': d['english_name'], 'category': d['category'], 'slug': d['slug'], 'reason': reason} for d, reason in missing], f, ensure_ascii=False, indent=2)
