"""Evaluate a frozen model on declared out-of-scope images, without tuning it.

Use --controls for synthetic plumbing checks only. Those are NOT a real OOD set.
"""
import argparse
import csv
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from PIL import Image, ImageDraw
from app.modules.images.image_analysis import decode_image, inspect_quality
from app.modules.images.image_model import read_configuration, score_image


def decision(scores, card):
    if (len(scores) != len(card.labels) or len(scores) < 2
            or any(not math.isfinite(s) or not 0 <= s <= 1 for s in scores)
            or abs(sum(scores) - 1) > .001):
        raise ValueError('Invalid model scores')
    ordered = sorted(scores, reverse=True)
    return ordered[0] >= card.minimum_score and ordered[0] - ordered[1] >= card.minimum_margin


def evaluate(images, card, checkpoint, scorer=score_image):
    rows = []
    for identifier, image in images:
        quality = inspect_quality(image)
        if any(issue['code'] != 'low_resolution' for issue in quality['issues']):
            rows.append({'image': identifier, 'decision': 'quality_review_required',
                         'issues': [issue['code'] for issue in quality['issues']]})
            continue
        scores = scorer(image, card, checkpoint)
        accepted = decision(scores, card)
        rows.append({'image': identifier, 'decision': 'accepted_unknown' if accepted else 'abstained',
                     'top_score': round(max(scores), 6)})
    counts = Counter(row['decision'] for row in rows)
    return {'images': len(rows), 'counts': dict(counts),
            'accepted_unknown_rate': counts['accepted_unknown'] / len(rows) if rows else None,
            'rows': rows}


def controls():
    for name, value in [('dark', 0), ('bright', 255), ('flat', 128)]:
        yield name, Image.new('RGB', (512, 512), (value, value, value))
    image = Image.new('RGB', (512, 512), (100, 130, 155))
    draw = ImageDraw.Draw(image)
    for x in range(0, 512, 12):
        draw.line((x, 0, x, 511), fill=(160, 175, 185), width=3)
    for y in range(0, 512, 15):
        draw.line((0, y, 511, y), fill=(70, 85, 110), width=2)
    yield 'synthetic_grid', image


def main(args):
    configured = read_configuration(args.model_card)
    if not configured:
        raise ValueError('No model configured')
    card, checkpoint = configured
    output = Path(args.output)
    if output.exists():
        raise FileExistsError('Preserve previous reports; choose a new output file')
    invalid, overlaps = [], []
    if args.controls:
        images = list(controls())
    else:
        if not args.unknown_dir or not args.manifest:
            raise ValueError('Real unknown images require --unknown-dir and the training --manifest')
        folder = Path(args.unknown_dir)
        if not folder.is_dir():
            raise ValueError('Unknown image directory does not exist')
        with Path(args.manifest).open(encoding='utf-8-sig', newline='') as stream:
            known_hashes = {row['sha256'] for row in csv.DictReader(stream)}
        def unknown_images():
            seen = set()
            for path in sorted(folder.rglob('*')):
                if not path.is_file() or path.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp'}:
                    continue
                relative = str(path.relative_to(folder))
                try:
                    if path.stat().st_size > 5 * 1024 * 1024:
                        raise ValueError('File too large')
                    data = path.read_bytes()
                    sha = hashlib.sha256(data).hexdigest()
                    if sha in known_hashes:
                        overlaps.append(relative)
                        continue
                    if sha in seen:
                        continue
                    seen.add(sha)
                    image, _, _ = decode_image(data)
                except Exception as error:
                    invalid.append({'image': relative, 'error': type(error).__name__})
                    continue
                yield relative, image
        images = unknown_images()
    import torch
    torch.set_num_threads(args.threads)
    report = evaluate(images, card, checkpoint)
    if overlaps:
        raise ValueError('Unknown set overlaps training manifest; no evaluation report written')
    if not report['images']:
        raise ValueError('No valid unknown images found')
    report.update(model_version=card.version, checkpoint_sha256=card.checkpoint_sha256,
                  model_card_policy={'minimum_score': card.minimum_score, 'minimum_margin': card.minimum_margin,
                                     'temperature': card.temperature},
                  policy_changed=False, synthetic_controls=args.controls,
                  real_ood_evaluation=not args.controls, invalid_files=invalid,
                  notice='Unknown labels are supplied by the evaluator. This report does not establish clinical validity or reliable OOD detection.')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({k: v for k, v in report.items() if k != 'rows'}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-card')
    parser.add_argument('--unknown-dir')
    parser.add_argument('--manifest')
    parser.add_argument('--controls', action='store_true')
    parser.add_argument('--output', required=True)
    parser.add_argument('--threads', type=int, default=4)
    main(parser.parse_args())
