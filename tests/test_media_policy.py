import io
import unittest

from PIL import Image

from app.core.media_policy import (
    MAX_ASSETS_PER_USER,
    MAX_USER_STORAGE_BYTES,
    MediaValidationError,
    media_quota_allows,
    sanitize_image,
)


def image_bytes(fmt="PNG", size=(32, 18), exif=None):
    image = Image.new("RGB", size, "red")
    output = io.BytesIO()
    image.save(output, format=fmt, exif=exif or b"")
    return output.getvalue()


class MediaPolicyTests(unittest.TestCase):
    def test_normalizes_supported_formats_and_builds_bounded_preview(self):
        result = sanitize_image(image_bytes("PNG", (1200, 700)))
        with Image.open(io.BytesIO(result.original)) as normalized:
            self.assertEqual(normalized.format, "JPEG")
            self.assertEqual(normalized.size, (1200, 700))
            self.assertEqual(normalized.getexif(), {})
        with Image.open(io.BytesIO(result.preview)) as preview:
            self.assertEqual(preview.format, "JPEG")
            self.assertLessEqual(max(preview.size), 640)

    def test_strips_exif_when_normalizing_jpeg(self):
        exif = Image.Exif()
        exif[270] = "private GPS-like description"
        result = sanitize_image(image_bytes("JPEG", exif=exif))
        with Image.open(io.BytesIO(result.original)) as normalized:
            self.assertEqual(normalized.getexif(), {})

    def test_rejects_empty_oversized_invalid_and_unsupported_files(self):
        for data in (b"", b"not an image", b"x" * (10 * 1024 * 1024 + 1), image_bytes("GIF")):
            with self.subTest(size=len(data)):
                with self.assertRaises(MediaValidationError):
                    sanitize_image(data)

    def test_rejects_excessive_pixel_dimensions(self):
        with self.assertRaises(MediaValidationError):
            sanitize_image(image_bytes("PNG", (7000, 6000)))

    def test_per_account_quota_accepts_exact_storage_edge_and_rejects_overflow(self):
        self.assertTrue(media_quota_allows(MAX_ASSETS_PER_USER - 1, MAX_USER_STORAGE_BYTES - 100, 100))
        self.assertFalse(media_quota_allows(MAX_ASSETS_PER_USER, 0, 1))
        self.assertFalse(media_quota_allows(0, MAX_USER_STORAGE_BYTES, 1))
        with self.assertRaises(ValueError):
            media_quota_allows(0, -1, 1)


if __name__ == "__main__":
    unittest.main()
