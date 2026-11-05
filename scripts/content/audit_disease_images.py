"""Export image coverage for every record in the input snapshot; does not query or change SQL."""
import json,csv,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'storage/temporary/disease-covers';DEST=ROOT/'storage/exports/disease-images';DEST.mkdir(parents=True,exist_ok=True)
norm=lambda s:' '.join((s or '').casefold().split())
metadata={}
for file in (OUT/'metadata-cache').glob('*.json'):
 for item in json.loads(file.read_text(encoding='utf-8')).get('query',{}).get('pages',{}).values():
  if item.get('imageinfo'):metadata[item['title'].replace('_',' ')]=item['imageinfo'][0]
notes=json.loads((OUT/'review-notes.json').read_text(encoding='utf-8')).get('rejected',{}) if (OUT/'review-notes.json').exists() else {}
records=json.loads((OUT/'library-records.json').read_text(encoding='utf-8'))
registry=json.loads((ROOT/'frontend/public/assets/library/diseases/credits.json').read_text(encoding='utf-8'));covers={norm(n):r for r in registry for n in r['names']}
candidates={norm(r['name']):r for r in json.loads((OUT/'all-discovery.json').read_text(encoding='utf-8'))}
counts={};report=[]
for r in records:
 name=norm(r.get('english_name'));cover=covers.get(name);candidate=candidates.get(name)
 status='Đã có ảnh được kiểm tra' if cover else 'Có ảnh ứng viên, chưa được chọn' if candidate else 'Chưa tìm được ảnh phù hợp trong đợt rà soát'
 counts[status]=counts.get(status,0)+1
 candidate_info=metadata.get('File:'+candidate['page']['pageimage'].replace('_',' '),{}) if candidate else {}
 candidate_license=candidate_info.get('extmetadata',{}).get('LicenseShortName',{}).get('value','')
 verdict=notes.get(name.replace(' ','-'),'')
 report.append([r['disease_id'],r['name'],r.get('english_name',''),status,cover['sourceUrl'] if cover else '',cover['license'] if cover else '',candidate['resolved'] if candidate else '',candidate_info.get('descriptionurl',''),candidate_license,verdict])
with (DEST/'ra-soat-anh-toan-bo-thu-vien.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['Mã bản ghi','Tên tiếng Việt','Tên tiếng Anh','Tình trạng ảnh','Nguồn ảnh đã duyệt','Giấy phép','Chủ đề ứng viên','Nguồn ảnh ứng viên chưa duyệt','Giấy phép ảnh ứng viên','Ghi chú kiểm tra']);w.writerows(report)
source=json.loads((OUT/'record-source.json').read_text(encoding='utf-8')).get('source') if (OUT/'record-source.json').exists() else 'Export snapshot 20261020T235915095684Z; live SQL connection unavailable'
summary=dict(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),source=source,records=len(records),image_assets=len(registry),candidate_names=len(candidates),coverage=counts)
(DEST/'ket-qua.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(summary,ensure_ascii=True))
