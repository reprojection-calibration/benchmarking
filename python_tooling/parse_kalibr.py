import argparse
import csv
from pathlib import Path

import yaml

CAMCHAIN_SUFFIX = "-camchain.yaml"


def collect_camchain_files(kalibr_directory):
    kalibr_directory = Path(kalibr_directory)

    camchain_files = sorted(kalibr_directory.glob(f"*/*{CAMCHAIN_SUFFIX}"))

    if not camchain_files:
        raise RuntimeError(f"No camchain YAML files found under {kalibr_directory}")

    return camchain_files


def load_camchain(path):
    path = Path(path)

    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict) or len(data) != 1:
        raise ValueError(f"Expected exactly one camera in {path}")

    return data, path


# WARN(Jack): Camera only!
def parse_camchain(input):
    data, path = input

    sensor, camera = next(iter(data.items()))

    intrinsics = camera["intrinsics"]
    resolution = camera["resolution"]

    if len(intrinsics) != 6:
        raise ValueError(
            f"Expected 6 double-sphere intrinsics in {path}, "
            f"but found {len(intrinsics)}"
        )

    xi, alpha, fx, fy, cx, cy = intrinsics
    width, height = resolution

    bag = path.name.removesuffix(CAMCHAIN_SUFFIX)

    # TODO COMBINE THE CAMERA MODEL AND DISTORTION MODEL INTO ONE
    # TODO AVERAGE THE FOCAL LENGTHS INTO ONE ELEMENT!
    return {
        "bag": bag,
        "sensor": sensor,
        "sensor_directory": path.parent.name,
        "topic": camera["rostopic"],
        "camera_model": camera["camera_model"],
        "distortion_model": camera["distortion_model"],
        "xi": xi,
        "alpha": alpha,
        "fx": fx,
        "fy": fy,
        "cx": cx,
        "cy": cy,
        "width": width,
        "height": height,
        "source_file": str(path),
    }


def arg_parser():
    parser = argparse.ArgumentParser(
        description="Extract Kalibr camera intrinsics from camchain YAML files."
    )
    parser.add_argument(
        "kalibr_directory",
        type=Path,
        help="Directory containing Kalibr camera result directories.",
    )
    parser.add_argument(
        "output_csv",
        type=Path,
        help="CSV file to create.",
    )
    args = parser.parse_args()


def main():
    args = arg_parser()

    camchain_files = collect_camchain_files(args.kalibr_directory)

    rows = [parse_camchain(load_camchain(path)) for path in camchain_files]

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)

    with args.output_csv.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} calibration results to {args.output_csv}")


if __name__ == "__main__":
    main()
