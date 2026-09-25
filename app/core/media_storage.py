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
    def put_pair(self, key: str, original: bytes, preview: bytes) -> None: ...
    def read(self, key: str) -> bytes: ...
    def delete_pair(self, key: str) -> None: ...


class LocalPrivateMediaStorage:
    """Private filesystem adapter. The configured directory must be a durable mount."""

    def __init__(self, root: str | None):
        self.root = Path(root).resolve() if root and root.strip() else None
        self.available = self.root is not None

    def ensure_available(self) -> None:
        if self.root is None:
            raise MediaStorageUnavailable("Хранилище файлов не настроено")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)

    def put_pair(self, key: str, original: bytes, preview: bytes) -> None:
        self.ensure_available()
        assert self.root is not None
        try:
            (self.root / f"{key}.jpg").write_bytes(original)
            (self.root / f"{key}-preview.jpg").write_bytes(preview)
        except Exception:
            (self.root / f"{key}.jpg").unlink(missing_ok=True)
            (self.root / f"{key}-preview.jpg").unlink(missing_ok=True)
            raise

    def read(self, key: str) -> bytes:
        self.ensure_available()
        assert self.root is not None
        return (self.root / f"{key}.jpg").read_bytes()

    def delete_pair(self, key: str) -> None:
        if self.root is None:
            return
        (self.root / f"{key}.jpg").unlink(missing_ok=True)
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

    def _key(self, key: str) -> str:
        return f"{self.prefix}/{key}.jpg" if self.prefix else f"{key}.jpg"

    def put_pair(self, key: str, original: bytes, preview: bytes) -> None:
        try:
            self.client.put_object(
                Bucket=self.bucket, Key=self._key(key), Body=original,
                ContentType="image/jpeg", CacheControl="private, no-store",
            )
            self.client.put_object(
                Bucket=self.bucket, Key=self._key(f"{key}-preview"), Body=preview,
                ContentType="image/jpeg", CacheControl="private, no-store",
            )
        except Exception:
            try:
                self.delete_pair(key)
            except Exception:
                pass
            raise

    def read(self, key: str) -> bytes:
        result = self.client.get_object(Bucket=self.bucket, Key=self._key(key))
        return result["Body"].read()

    def delete_pair(self, key: str) -> None:
        for object_key in (self._key(key), self._key(f"{key}-preview")):
            self.client.delete_object(Bucket=self.bucket, Key=object_key)


class DisabledMediaStorage:
    available = False

    def __init__(self, reason: str = "Хранилище файлов не настроено"):
        self.reason = reason

    def ensure_available(self) -> None:
        raise MediaStorageUnavailable(self.reason)

    def put_pair(self, key: str, original: bytes, preview: bytes) -> None:
        self.ensure_available()

    def read(self, key: str) -> bytes:
        self.ensure_available()
        raise AssertionError("unreachable")

    def delete_pair(self, key: str) -> None:
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
