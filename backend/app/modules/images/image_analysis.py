"""Image inspection only: heuristic quality checks do not identify skin or disease."""

import io
import warnings
from PIL import Image, ImageOps, ImageStat
from fastapi import HTTPException
from pydantic import BaseModel, Field, model_validator

MAX_BYTES = 5 * 1024 * 1024
MIN_SIDE = 224


class Crop(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def inside_image(self):
        if self.x + self.width > 1.000001 or self.y + self.height > 1.000001:
            raise ValueError("Vùng chọn vượt ra ngoài ảnh")
        return self


def decode_image(content, crop=None):
    if len(content) > MAX_BYTES:
        raise HTTPException(413, "Ảnh vượt quá giới hạn 5 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as source:
                if source.format not in {"JPEG", "PNG", "WEBP"}:
                    raise HTTPException(415, "Chỉ hỗ trợ ảnh JPEG, PNG hoặc WebP.")
                if source.width * source.height > 12_000_000:
                    raise HTTPException(422, "Ảnh vượt quá 12 triệu điểm ảnh.")
                if getattr(source, "n_frames", 1) != 1:
                    raise HTTPException(422, "Vui lòng dùng ảnh tĩnh.")
                source.load()
                fmt = source.format
                image = ImageOps.exif_transpose(source).copy()
        original_width, original_height = image.size
        if min(image.size) < MIN_SIDE:
            raise HTTPException(422, "Ảnh quá nhỏ. Mỗi chiều cần ít nhất 224 pixel.")
        bounds = None
        if crop:
            left = round(crop.x * image.width)
            top = round(crop.y * image.height)
            right = min(image.width, round((crop.x + crop.width) * image.width))
            bottom = min(image.height, round((crop.y + crop.height) * image.height))
            bounds = {"x": left, "y": top, "width": right - left, "height": bottom - top}
            if min(right - left, bottom - top) < MIN_SIDE:
                raise HTTPException(
                    422, "Vùng chọn quá nhỏ. Mỗi chiều của vùng chọn cần ít nhất 224 pixel."
                )
            image = image.crop((left, top, right, bottom))
        transparency = 0.0
        if "A" in image.getbands() or "transparency" in image.info:
            rgba = image.convert("RGBA")
            alpha = rgba.getchannel("A")
            alpha.thumbnail((512, 512))
            hist = alpha.histogram()
            transparency = sum(hist[:250]) / sum(hist)
            canvas = Image.new("RGBA", rgba.size, (127, 127, 127, 255))
            image = Image.alpha_composite(canvas, rgba).convert("RGB")
        else:
            image = image.convert("RGB")
        # A new pixel-only image drops EXIF and other user metadata before inference.
        clean = Image.new("RGB", image.size)
        clean.paste(image)
        return (
            clean,
            {
                "width": clean.width,
                "height": clean.height,
                "original_width": original_width,
                "original_height": original_height,
                "format": fmt,
                "crop": bounds,
            },
            transparency,
        )
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        ValueError,
    ) as exc:
        raise HTTPException(422, "Không thể đọc ảnh hoặc ảnh vượt giới hạn an toàn.") from exc


def inspect_quality(image, transparency=0.0):
    gray = image.convert("L")
    gray.thumbnail((512, 512), Image.Resampling.LANCZOS)
    hist = gray.histogram()
    total = gray.width * gray.height
    mean = ImageStat.Stat(gray).mean[0]
    contrast = ImageStat.Stat(gray).stddev[0]
    dark = sum(hist[:11]) / total
    bright = sum(hist[245:]) / total
    # Finite differences on bounded thumbnail, without numpy or model dependencies.
    pixels = list(gray.get_flattened_data())
    width = gray.width
    height = gray.height
    edges = []
    for y in range(1, height - 1):
        offset = y * width
        for x in range(1, width - 1):
            i = offset + x
            edges.append(
                pixels[i - 1]
                + pixels[i + 1]
                + pixels[i - width]
                + pixels[i + width]
                - 4 * pixels[i]
            )
    edge_mean = sum(edges) / len(edges) if edges else 0
    detail = sum((v - edge_mean) ** 2 for v in edges) / len(edges) if edges else 0
    lighting = (
        "low" if mean < 40 or dark > 0.65 else "high" if mean > 220 or bright > 0.65 else "balanced"
    )
    detail_status = "limited" if contrast < 12 or detail < 18 else "visible"
    issues = []
    if lighting == "low":
        issues.append(
            {
                "code": "too_dark",
                "message": "Ảnh có nhiều vùng tối. Hãy thử ánh sáng đều hơn, tránh bóng che.",
            }
        )
    if lighting == "high":
        issues.append(
            {
                "code": "too_bright",
                "message": "Ảnh có nhiều vùng sáng trắng. Hãy giảm ánh sáng gắt hoặc tránh phản chiếu.",
            }
        )
    if detail_status == "limited":
        issues.append(
            {
                "code": "limited_detail",
                "message": "Ít chi tiết được ghi nhận: ảnh có thể mờ hoặc bề mặt ít tương phản. Kiểm tra ảnh gốc và thử lấy nét lại.",
            }
        )
    if min(image.size) < 384:
        issues.append(
            {
                "code": "low_resolution",
                "message": "Vùng ảnh khá nhỏ. Ảnh lớn hơn có thể giúp kiểm tra chi tiết tốt hơn.",
            }
        )
    if transparency > 0.1:
        issues.append(
            {
                "code": "transparency",
                "message": "Ảnh có vùng trong suốt. Hãy dùng ảnh chụp gốc có nền đầy đủ.",
            }
        )
    return {
        "version": "quality-heuristics-v1",
        "status": "needs_review" if issues else "no_obvious_issue",
        "metrics": {
            "brightness": round(mean, 2),
            "contrast": round(contrast, 2),
            "detail_variance": round(detail, 2),
            "dark_fraction": round(dark, 4),
            "bright_fraction": round(bright, 4),
        },
        "lighting": lighting,
        "detail": detail_status,
        "issues": issues,
        "notice": "Các chỉ số kỹ thuật là ước lượng, phụ thuộc nội dung và tông màu ảnh. Không xác nhận đây là ảnh da, chất lượng y khoa hoặc bệnh lý.",
    }
