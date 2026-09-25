import tempfile
import unittest
from pathlib import Path

from app.core.media_storage import (
    DisabledMediaStorage,
    LocalPrivateMediaStorage,
    S3PrivateMediaStorage,
    create_media_storage,
)


class FakeBody:
    def __init__(self, value):
        self.value = value

    def read(self):
        return self.value


class FakeS3:
    def __init__(self):
        self.objects = {}
        self.put_calls = []
        self.delete_calls = []

    def put_object(self, **kwargs):
        self.put_calls.append(kwargs)
        self.objects[(kwargs["Bucket"], kwargs["Key"])] = kwargs["Body"]

    def get_object(self, **kwargs):
        return {"Body": FakeBody(self.objects[(kwargs["Bucket"], kwargs["Key"])])}

    def delete_object(self, **kwargs):
        self.delete_calls.append(kwargs)
        self.objects.pop((kwargs["Bucket"], kwargs["Key"]), None)


class MediaStorageTests(unittest.TestCase):
    def test_s3_adapter_keeps_objects_private_and_round_trips_both_variants(self):
        client = FakeS3()
        storage = S3PrivateMediaStorage(client, "private-bucket", "/crista/photos/")
        storage.put_pair("random-key", b"original", b"preview", "image/jpeg")
        self.assertEqual(storage.read("random-key"), b"original")
        self.assertEqual(storage.read("random-key-preview"), b"preview")
        self.assertEqual([call["Key"] for call in client.put_calls], [
            "crista/photos/random-key.jpg", "crista/photos/random-key-preview.jpg",
        ])
        self.assertTrue(all("ACL" not in call for call in client.put_calls))
        self.assertTrue(all(call["CacheControl"] == "private, no-store" for call in client.put_calls))
        storage.delete_pair("random-key")
        self.assertEqual(len(client.delete_calls), 2)
        self.assertEqual(client.objects, {})

    def test_filesystem_adapter_round_trips_and_deletes_files(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = LocalPrivateMediaStorage(directory)
            storage.put_pair("safe-random-key", b"original", b"preview", "image/jpeg")
            self.assertEqual(storage.read("safe-random-key-preview"), b"preview")
            self.assertEqual(oct(Path(directory).stat().st_mode & 0o777), "0o700")
            storage.delete_pair("safe-random-key")
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_adapters_select_video_extension_but_keep_preview_as_jpeg(self):
        client = FakeS3()
        storage = S3PrivateMediaStorage(client, "private-bucket")
        storage.put_pair("video-key", b"mp4", b"poster", "video/mp4")
        self.assertIn(("private-bucket", "crista-media/video-key.mp4"), client.objects)
        self.assertIn(("private-bucket", "crista-media/video-key-preview.jpg"), client.objects)
        self.assertEqual(client.put_calls[0]["ContentType"], "video/mp4")
        self.assertEqual(storage.read("video-key", "video/mp4"), b"mp4")
        storage.delete_pair("video-key", "video/mp4")
        self.assertEqual(client.objects, {})

    def test_factory_fails_closed_for_unconfigured_or_invalid_storage(self):
        self.assertIsInstance(create_media_storage({}), DisabledMediaStorage)
        self.assertFalse(create_media_storage({"MEDIA_STORAGE_BACKEND": "local"}).available)
        invalid = create_media_storage({"MEDIA_STORAGE_BACKEND": "unknown"})
        self.assertIsInstance(invalid, DisabledMediaStorage)
        with self.assertRaisesRegex(RuntimeError, "MEDIA_STORAGE_BACKEND"):
            invalid.ensure_available()

    def test_s3_factory_requires_explicit_endpoint_bucket_credentials_and_region(self):
        result = create_media_storage({"MEDIA_STORAGE_BACKEND": "s3", "MEDIA_S3_SECRET_ACCESS_KEY": "do-not-echo"})
        self.assertFalse(result.available)
        self.assertNotIn("do-not-echo", result.reason)

    def test_s3_factory_rejects_plaintext_remote_endpoint(self):
        result = create_media_storage({
            "MEDIA_STORAGE_BACKEND": "s3", "MEDIA_S3_ENDPOINT_URL": "http://storage.example.test",
            "MEDIA_S3_BUCKET": "bucket", "MEDIA_S3_REGION": "region",
            "MEDIA_S3_ACCESS_KEY_ID": "public-id", "MEDIA_S3_SECRET_ACCESS_KEY": "secret",
        })
        self.assertFalse(result.available)
        self.assertEqual(result.reason, "S3 endpoint должен использовать HTTPS")

    def test_s3_factory_never_accepts_credentials_embedded_in_endpoint(self):
        result = create_media_storage({
            "MEDIA_STORAGE_BACKEND": "s3", "MEDIA_S3_ENDPOINT_URL": "https://user:secret@storage.example.test",
            "MEDIA_S3_BUCKET": "bucket", "MEDIA_S3_REGION": "region",
            "MEDIA_S3_ACCESS_KEY_ID": "public-id", "MEDIA_S3_SECRET_ACCESS_KEY": "secret",
        })
        self.assertFalse(result.available)
        self.assertNotIn("secret", result.reason)


if __name__ == "__main__":
    unittest.main()
