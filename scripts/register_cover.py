import json
import sys
from pathlib import Path
from PIL import Image

def register_cover(source_image_path, key, names, caption="Minh họa khái niệm, không phải ảnh lâm sàng."):
    source_path = Path(source_image_path)
    if not source_path.exists():
        print(f"Error: Source image not found: {source_path}")
        return False
        
    illustrations_dir = Path("f:/App/Codex/derma-library/frontend/public/assets/library/illustrations")
    dest_webp = illustrations_dir / f"{key}.webp"
    
    with Image.open(source_path) as img:
        img.save(dest_webp, "WEBP", quality=90)
    print(f"Saved WEBP to: {dest_webp}")
    
    covers_file = Path("f:/App/Codex/derma-library/frontend/src/shared/data/diseaseCovers.json")
    with open(covers_file, "r", encoding="utf-8") as f:
        covers = json.load(f)
        
    existing_index = next((i for i, c in enumerate(covers) if c.get("key") == key), None)
    entry = {
        "key": key,
        "names": names,
        "src": f"/assets/library/illustrations/{key}.webp",
        "sourceUrl": "",
        "creator": "AI-generated illustration",
        "license": "AI-generated; conceptual educational illustration",
        "licenseUrl": "",
        "assetType": "illustration",
        "caption": caption
    }
    
    if existing_index is not None:
        covers[existing_index] = entry
        print(f"Updated existing entry for {key}")
    else:
        covers.append(entry)
        print(f"Added new entry for {key}")
        
    with open(covers_file, "w", encoding="utf-8") as f:
        json.dump(covers, f, ensure_ascii=False, indent=2)
    print("Updated diseaseCovers.json successfully.")
    return True

if __name__ == "__main__":
    if len(sys.argv) >= 4:
        img_path = sys.argv[1]
        key = sys.argv[2]
        names = sys.argv[3].split("|")
        register_cover(img_path, key, names)
