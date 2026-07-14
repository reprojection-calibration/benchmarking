import tempfile
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from unittest import TestCase

from parse_kalibr import (CAMCHAIN_SUFFIX, collect_camchain_files,
                          load_camchain, parse_camchain)


class TestParseKalibr(TestCase):
    def test_collect_camchain_files(self):
        # From - https://adamj.eu/tech/2024/12/30/python-temporary-files-directories-unittest/ - "enterContext() enters
        # the NamedTemporaryFile context manager and runs its exit method at the end of the test. Using enterContext()
        # avoids indenting the whole test, as would be required using with."
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

    def test_load_camchain(self):
        temp_file = self.enterContext(NamedTemporaryFile(mode="w+", suffix=".yaml"))
        temp_file.write(
            """
            foo:
              bar: 111
            """
        )
        temp_file.flush()

        result = load_camchain(temp_file.name)

        self.assertEqual(({"foo": {"bar": 111}}, Path(temp_file.name)), result)
