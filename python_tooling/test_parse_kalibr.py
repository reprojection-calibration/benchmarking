import tempfile
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from unittest import TestCase

import yaml

from parse_kalibr import (
    CAMCHAIN_SUFFIX,
    collect_camchain_files,
    load_camchain,
    parse_camchain,
)


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

    def test_parse_camchain(self):
        yaml_text = """
            cam0:
              cam_overlaps: []
              camera_model: ds
              distortion_coeffs: []
              distortion_model: none
              intrinsics: [1, 2, 3, 4, 5, 6]
              resolution: [512, 512]
              rostopic: /cam0/image_raw
            """

        data = yaml.safe_load(yaml_text)

        result = parse_camchain((data, f"foo/bar{CAMCHAIN_SUFFIX}"))

        self.assertEqual(
            result,
            {
                "bag": "bar",
                "sensor_directory": "foo",
                "sensor_name": "/cam0/image_raw",
                "camera_model": "ds-none",
                "fx": 3,
                "fy": 4,
                "cx": 5,
                "cy": 6,
                "xi": 1,
                "alpha": 2,
                "width": 512,
                "height": 512,
                "source_file": "foo/bar-camchain.yaml",
            },
        )
