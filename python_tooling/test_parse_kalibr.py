import tempfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from parse_kalibr import (CAMCHAIN_SUFFIX, collect_camchain_files,
                          load_camchain, parse_camchain)


class TestParseKalibr(TestCase):
    def test_collect_camchain_files(self):
        temp_dir = self.enterContext(TemporaryDirectory())
        for camera in ("cam0_image_raw", "cam1_image_raw"):
            camera_dir = Path(temp_dir) / camera
            camera_dir.mkdir()

            (camera_dir / f"foo-bar{CAMCHAIN_SUFFIX}").write_text("foo bar")

        camchain_files = collect_camchain_files(temp_dir)

        self.assertEqual(
            camchain_files,
            [
                Path(f"{temp_dir}/cam0_image_raw/foo-bar-camchain.yaml"),
                Path(f"{temp_dir}/cam1_image_raw/foo-bar-camchain.yaml"),
            ],
        )
