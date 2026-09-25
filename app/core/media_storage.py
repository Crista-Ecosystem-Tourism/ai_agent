"""Storage seam and private filesystem/S3-compatible adapters for user media."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping, Protocol
from urllib.parse import urlsplit


class MediaStorageUnavailable(RuntimeError):
    pass


class MediaStorage(Protocol):
    available: bool

    def ensure_available(self) -> None: ...
    def put_pair(self, key: str, original: bytes, preview: bytes, content_type: str) -> None: ...
    def read(self, key: str, content_type: str = "image/jpeg") -> bytes: ...
    def delete_pair(self, key: str, content_type: str = "image/jpeg") -> None: ...


def _extension(content_type: str) -> str:
    extensions = {"image/jpeg": "jpg", "video/mp4": "mp4", "video/webm": "webm"}
    try:
        return extensions[content_type]
    except KeyError as error:
        raise MediaStorageUnavailable("Unsupported media type") from error


class LocalPrivateMediaStorage:
    """Private filesystem adapter. The configured directory must be a durable mount."""

    def __init__(self, root: str | None):
        self.root = Path(root).resolve() if root and root.strip() else None
        self.available = self.root is not None

    def ensure_available(self) -> None:
        if self.root is None:
            raise MediaStorageUnavailable("Хранилище файлов не настроено")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)

    def put_pair(self, key: str, original: bytes, preview: bytes, content_type: str) -> None:
        self.ensure_available()
        assert self.root is not None
        original_path = self.root / f"{key}.{_extension(content_type)}"
        preview_path = self.root / f"{key}-preview.jpg"
        try:
            original_path.write_bytes(original)
            preview_path.write_bytes(preview)
        except Exception:
            original_path.unlink(missing_ok=True)
            preview_path.unlink(missing_ok=True)
            raise

    def read(self, key: str, content_type: str = "image/jpeg") -> bytes:
        self.ensure_available()
        assert self.root is not None
        return (self.root / f"{key}.{_extension(content_type)}").read_bytes()

    def delete_pair(self, key: str, content_type: str = "image/jpeg") -> None:
        if self.root is None:
            return
        (self.root / f"{key}.{_extension(content_type)}").unlink(missing_ok=True)
        (self.root / f"{key}-preview.jpg").unlink(missing_ok=True)


class S3PrivateMediaStorage:
    """S3-compatible adapter; objects stay private and are never exposed as public URLs."""

    def __init__(self, client, bucket: str, prefix: str = "crista-media"):
        self.client = client
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self.available = True

    def ensure_available(self) -> None:
        return None

    def _key(self, key: str, content_type: str) -> str:
        filename = f"{key}.{_extension(content_type)}"
        return f"{self.prefix}/{filename}" if self.prefix else filename

    def put_pair(self, key: str, original: bytes, preview: bytes, content_type: str) -> None:
        try:
            self.client.put_object(
                Bucket=self.bucket, Key=self._key(key, content_type), Body=original,
                ContentType=content_type, CacheControl="private, no-store",
            )
            self.client.put_object(
                Bucket=self.bucket, Key=self._key(f"{key}-preview", "image/jpeg"), Body=preview,
                ContentType="image/jpeg", CacheControl="private, no-store",
            )
        except Exception:
            try:
                self.delete_pair(key, content_type)
            except Exception:
                pass
            raise

    def read(self, key: str, content_type: str = "image/jpeg") -> bytes:
        result = self.client.get_object(Bucket=self.bucket, Key=self._key(key, content_type))
        return result["Body"].read()

    def delete_pair(self, key: str, content_type: str = "image/jpeg") -> None:
        for object_key in (self._key(key, content_type), self._key(f"{key}-preview", "image/jpeg")):
            self.client.delete_object(Bucket=self.bucket, Key=object_key)


class DisabledMediaStorage:
    available = False

    def __init__(self, reason: str = "Хранилище файлов не настроено"):
        self.reason = reason

    def ensure_available(self) -> None:
        raise MediaStorageUnavailable(self.reason)

    def put_pair(self, key: str, original: bytes, preview: bytes, content_type: str) -> None:
        self.ensure_available()

    def read(self, key: str, content_type: str = "image/jpeg") -> bytes:
        self.ensure_available()
        raise AssertionError("unreachable")

    def delete_pair(self, key: str, content_type: str = "image/jpeg") -> None:
        self.ensure_available()


def create_media_storage(environ: Mapping[str, str] | None = None) -> MediaStorage:
    env = environ if environ is not None else os.environ
    kind = (env.get("MEDIA_STORAGE_BACKEND") or "disabled").strip().lower()
    if kind == "disabled":
        return DisabledMediaStorage()
    if kind == "local":
        return LocalPrivateMediaStorage(env.get("MEDIA_STORAGE_DIR"))
    if kind != "s3":
        return DisabledMediaStorage("MEDIA_STORAGE_BACKEND должен быть local, s3 или disabled")

    endpoint = (env.get("MEDIA_S3_ENDPOINT_URL") or "").strip()
    bucket = (env.get("MEDIA_S3_BUCKET") or "").strip()
    access_key = (env.get("MEDIA_S3_ACCESS_KEY_ID") or "").strip()
    secret_key = (env.get("MEDIA_S3_SECRET_ACCESS_KEY") or "").strip()
    region = (env.get("MEDIA_S3_REGION") or "").strip()
    if not all((endpoint, bucket, access_key, secret_key, region)):
        return DisabledMediaStorage("Конфигурация S3-хранилища неполна")
    try:
        parsed_endpoint = urlsplit(endpoint)
        hostname = parsed_endpoint.hostname
    except ValueError:
        return DisabledMediaStorage("Некорректный MEDIA_S3_ENDPOINT_URL")
    if not hostname or parsed_endpoint.username or parsed_endpoint.password or parsed_endpoint.query or parsed_endpoint.fragment:
        return DisabledMediaStorage("Некорректный MEDIA_S3_ENDPOINT_URL")
    if parsed_endpoint.scheme not in {"https", "http"}:
        return DisabledMediaStorage("MEDIA_S3_ENDPOINT_URL должен использовать HTTP(S)")
    if parsed_endpoint.scheme != "https" and hostname not in {"localhost", "127.0.0.1", "::1"}:
        return DisabledMediaStorage("S3 endpoint должен использовать HTTPS")
    try:
        import boto3
        from botocore.config import Config

        client = boto3.client(
            "s3", endpoint_url=endpoint, region_name=region,
            aws_access_key_id=access_key, aws_secret_access_key=secret_key,
            config=Config(s3={"addressing_style": "path"}),
        )
    except ImportError:
        return DisabledMediaStorage("S3-адаптер недоступен: не установлен boto3")
    except Exception:
        return DisabledMediaStorage("S3-адаптер не удалось настроить")
    return S3PrivateMediaStorage(client, bucket, env.get("MEDIA_S3_PREFIX", "crista-media"))
