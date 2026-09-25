import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from app.core.media_policy import MediaValidationError, sanitize_media


FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")


@unittest.skipUnless(FFMPEG and FFPROBE, "FFmpeg/FFprobe are installed by the API runtime image")
class VideoMediaPolicyTests(unittest.TestCase):
    def make_video(self, directory: str) -> bytes:
        path = Path(directory) / "source.mp4"
        subprocess.run([
            FFMPEG, "-nostdin", "-hide_banner", "-v", "error", "-f", "lavfi", "-i",
            "color=c=blue:s=64x48:d=2:r=10", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-metadata", "title=private metadata", "-movflags", "+faststart", str(path),
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=20)
        return path.read_bytes()

    def test_remuxes_video_strips_metadata_and_generates_poster(self):
        with tempfile.TemporaryDirectory() as directory:
            source = self.make_video(directory)
        result = sanitize_media(source)
        self.assertEqual(result.content_type, "video/mp4")
        self.assertEqual((result.width, result.height), (64, 48))
        self.assertEqual(result.duration_seconds, 2)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "clean.mp4"
            output.write_bytes(result.original)
            probe = subprocess.run([
                FFPROBE, "-v", "error", "-show_entries", "format_tags:stream_tags", "-of", "json", str(output),
            ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            metadata = json.loads(probe.stdout)
            tags = metadata.get("format", {}).get("tags", {})
            self.assertNotIn("title", {key.lower() for key in tags})
        with Image.open(io.BytesIO(result.preview)) as poster:
            self.assertEqual(poster.format, "JPEG")
            self.assertLessEqual(max(poster.size), 640)

    def test_rejects_invalid_video_container(self):
        with self.assertRaises(MediaValidationError):
            sanitize_media(b"\x00\x00\x00\x18ftypisom-invalid")


if __name__ == "__main__":
    unittest.main()
