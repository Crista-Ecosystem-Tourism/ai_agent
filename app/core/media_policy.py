"""Bounded, privacy-preserving image ingestion policy (independent of HTTP/DB)."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, UnidentifiedImageError


MAX_IMAGE_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_VIDEO_UPLOAD_BYTES = 50 * 1024 * 1024
MAX_UPLOAD_BYTES = MAX_VIDEO_UPLOAD_BYTES
MAX_VIDEO_DURATION_SECONDS = 60
MAX_VIDEO_PIXELS = 1920 * 1080
MAX_IMAGE_PIXELS = 40_000_000
MAX_ASSETS_PER_USER = 100
MAX_USER_STORAGE_BYTES = 250 * 1024 * 1024
PREVIEW_MAX_EDGE = 640
ACCEPTED_FORMATS = {"JPEG", "PNG", "WEBP"}


class MediaValidationError(ValueError):
    pass


class MediaProcessingUnavailable(RuntimeError):
    pass


def media_quota_allows(asset_count: int, stored_bytes: int, incoming_bytes: int) -> bool:
    if min(asset_count, stored_bytes, incoming_bytes) < 0:
        raise ValueError("Media quota values cannot be negative")
    return asset_count < MAX_ASSETS_PER_USER and stored_bytes + incoming_bytes <= MAX_USER_STORAGE_BYTES


@dataclass(frozen=True)
class SanitizedMedia:
    original: bytes
    preview: bytes
    width: int
    height: int
    content_type: str = "image/jpeg"
    duration_seconds: int | None = None


def sanitize_image(data: bytes) -> SanitizedMedia:
    if not data:
        raise MediaValidationError("Файл пуст")
    if len(data) > MAX_IMAGE_UPLOAD_BYTES:
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
            return SanitizedMedia(clean.getvalue(), preview.getvalue(), width, height)
    except MediaValidationError:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise MediaValidationError("Файл не является корректным изображением") from error


def _run_media_tool(command: list[str], timeout_seconds: int) -> subprocess.CompletedProcess:
    try:
        result = subprocess.run(
            command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=timeout_seconds, check=False,
        )
    except FileNotFoundError as error:
        raise MediaProcessingUnavailable("На сервере не установлен FFmpeg/FFprobe") from error
    except subprocess.TimeoutExpired as error:
        raise MediaProcessingUnavailable("Обработка видео превысила лимит времени") from error
    if result.returncode != 0:
        raise MediaValidationError("Видео повреждено или не поддерживается")
    return result


def sanitize_video(data: bytes) -> SanitizedMedia:
    if not data:
        raise MediaValidationError("Файл пуст")
    if len(data) > MAX_VIDEO_UPLOAD_BYTES:
        raise MediaValidationError("Максимальный размер видео — 50 МБ")
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise MediaProcessingUnavailable("На сервере не установлен FFmpeg/FFprobe")

    with tempfile.TemporaryDirectory(prefix="crista-media-") as directory:
        root = Path(directory)
        source = root / "upload.bin"
        source.write_bytes(data)
        probe = _run_media_tool([
            ffprobe, "-v", "error", "-protocol_whitelist", "file,pipe",
            "-show_entries", "format=format_name,duration:stream=codec_type,codec_name,width,height",
            "-of", "json", str(source),
        ], timeout_seconds=8)
        try:
            metadata = json.loads(probe.stdout)
            format_names = set(metadata["format"]["format_name"].split(","))
            duration_float = float(metadata["format"]["duration"])
            streams = metadata["streams"]
            video = next(stream for stream in streams if stream.get("codec_type") == "video")
            width, height = int(video["width"]), int(video["height"])
            codec = video["codec_name"]
        except (KeyError, TypeError, ValueError, StopIteration, json.JSONDecodeError) as error:
            raise MediaValidationError("Не удалось определить параметры видео") from error

        if "mp4" in format_names and codec == "h264":
            content_type, extension, muxer = "video/mp4", "mp4", "mp4"
        elif format_names.intersection({"webm", "matroska"}) and codec in {"vp8", "vp9", "av1"}:
            content_type, extension, muxer = "video/webm", "webm", "webm"
        else:
            raise MediaValidationError("Поддерживаются MP4/H.264 и WebM/VP8, VP9 или AV1")
        if not 0 < duration_float <= MAX_VIDEO_DURATION_SECONDS:
            raise MediaValidationError("Видео должно длиться не более 60 секунд")
        if width < 1 or height < 1 or width * height > MAX_VIDEO_PIXELS:
            raise MediaValidationError("Разрешение видео не должно превышать 1920×1080 пикселей")

        sanitized_path = root / f"sanitized.{extension}"
        remux = [
            ffmpeg, "-nostdin", "-hide_banner", "-v", "error", "-protocol_whitelist", "file,pipe",
            "-i", str(source), "-map", "0:v:0", "-map", "0:a:0?", "-c", "copy",
            "-map_metadata", "-1", "-map_metadata:s", "-1", "-map_chapters", "-1",
        ]
        if muxer == "mp4":
            remux.extend(["-movflags", "+faststart"])
        remux.extend(["-f", muxer, str(sanitized_path)])
        _run_media_tool(remux, timeout_seconds=20)
        sanitized_video = sanitized_path.read_bytes()
        if not sanitized_video or len(sanitized_video) > MAX_VIDEO_UPLOAD_BYTES:
            raise MediaValidationError("Размер обработанного видео превышает 50 МБ")

        preview_path = root / "preview.jpg"
        seek_seconds = min(1.0, duration_float / 2)
        _run_media_tool([
            ffmpeg, "-nostdin", "-hide_banner", "-v", "error", "-protocol_whitelist", "file,pipe",
            "-ss", f"{seek_seconds:.3f}", "-i", str(sanitized_path), "-frames:v", "1",
            "-vf", "scale=640:640:force_original_aspect_ratio=decrease", "-map_metadata", "-1",
            "-q:v", "3", str(preview_path),
        ], timeout_seconds=12)
        preview_data = preview_path.read_bytes()
        if not preview_data:
            raise MediaValidationError("Не удалось создать превью видео")
        return SanitizedMedia(
            original=sanitized_video, preview=preview_data, width=width, height=height,
            content_type=content_type, duration_seconds=max(1, round(duration_float)),
        )


def sanitize_media(data: bytes) -> SanitizedMedia:
    if data.startswith(b"\xFF\xD8\xFF") or data.startswith(b"\x89PNG\r\n\x1a\n") or (
        data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    ):
        return sanitize_image(data)
    if len(data) >= 12 and data[4:8] == b"ftyp":
        return sanitize_video(data)
    if data.startswith(b"\x1A\x45\xDF\xA3"):
        return sanitize_video(data)
    raise MediaValidationError("Разрешены JPEG, PNG, WebP, MP4 и WebM")
