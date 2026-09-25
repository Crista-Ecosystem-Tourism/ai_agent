"""Bounded, privacy-preserving image ingestion policy (independent of HTTP/DB)."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from PIL import Image, UnidentifiedImageError


MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
MAX_ASSETS_PER_USER = 100
MAX_USER_STORAGE_BYTES = 250 * 1024 * 1024
PREVIEW_MAX_EDGE = 640
ACCEPTED_FORMATS = {"JPEG", "PNG", "WEBP"}


class MediaValidationError(ValueError):
    pass


def media_quota_allows(asset_count: int, stored_bytes: int, incoming_bytes: int) -> bool:
    if min(asset_count, stored_bytes, incoming_bytes) < 0:
        raise ValueError("Media quota values cannot be negative")
    return asset_count < MAX_ASSETS_PER_USER and stored_bytes + incoming_bytes <= MAX_USER_STORAGE_BYTES


@dataclass(frozen=True)
class SanitizedImage:
    original: bytes
    preview: bytes
    width: int
    height: int


def sanitize_image(data: bytes) -> SanitizedImage:
    if not data:
        raise MediaValidationError("Файл пуст")
    if len(data) > MAX_UPLOAD_BYTES:
        raise MediaValidationError("Максимальный размер снимка — 10 МБ")
    try:
        with Image.open(BytesIO(data)) as probe:
            if probe.format not in ACCEPTED_FORMATS:
                raise MediaValidationError("Разрешены только JPEG, PNG и WebP")
            if getattr(probe, "n_frames", 1) != 1:
                raise MediaValidationError("Анимированные изображения пока не поддерживаются")
            width, height = probe.size
            if width < 1 or height < 1 or width * height > MAX_IMAGE_PIXELS:
                raise MediaValidationError("Недопустимые размеры изображения")
            probe.verify()
        with Image.open(BytesIO(data)) as source:
            image = source.convert("RGB")
            clean = BytesIO()
            image.save(clean, format="JPEG", quality=88, optimize=True)
            preview_image = image.copy()
            preview_image.thumbnail((PREVIEW_MAX_EDGE, PREVIEW_MAX_EDGE))
            preview = BytesIO()
            preview_image.save(preview, format="JPEG", quality=78, optimize=True)
            return SanitizedImage(clean.getvalue(), preview.getvalue(), width, height)
    except MediaValidationError:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise MediaValidationError("Файл не является корректным изображением") from error
