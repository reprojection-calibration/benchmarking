import argparse
import csv
import tomllib
from pathlib import Path

CALIBRATION_SUFFIX = ".calib.toml"


def collect_calibration_files(reprojection_directory):
    reprojection_directory = Path(reprojection_directory)

    calibration_files = sorted(reprojection_directory.glob(f"*{CALIBRATION_SUFFIX}"))

    if not calibration_files:
        raise RuntimeError(f"No Reprojection calibration TOML files found under " f"{reprojection_directory}")

    return calibration_files


def load_calibration(path):
    path = Path(path)

    with path.open("rb") as file:
        data = tomllib.load(file)

    if not isinstance(data, dict) or not data:
        raise ValueError(f"Expected at least one camera section in {path}")

    return data, path


# WARN(Jack): Camera only and hardcoded for the double-sphere model.
def parse_calibration(input):
    data, path = input
    path = Path(path)

    rows = []

    for sensor_directory, camera in data.items():
        if not isinstance(camera, dict):
            raise ValueError(f"Expected camera section '{sensor_directory}' in {path} " f"to be a TOML table")

        intrinsics = camera["intrinsics"]
        resolution = camera["resolution"]

        if len(intrinsics) != 5:
            raise ValueError(
                f"Expected 5 double-sphere intrinsics for "
                f"'{sensor_directory}' in {path}, "
                f"but found {len(intrinsics)}"
            )

        if len(resolution) != 2:
            raise ValueError(
                f"Expected a two-element resolution for "
                f"'{sensor_directory}' in {path}, "
                f"but found {len(resolution)}"
            )

        focal_length, cx, cy, xi, alpha = intrinsics
        width, height = resolution

        rows.append(
            {
                "bag": path.name.removesuffix(CALIBRATION_SUFFIX),
                "sensor_directory": sensor_directory,
                "sensor_name": camera["sensor_id"],
                "camera_model": camera["camera_model"],
                "fx": focal_length,
                "fy": focal_length,
                "cx": cx,
                "cy": cy,
                "xi": xi,
                "alpha": alpha,
                "width": width,
                "height": height,
                "source_file": str(path),
            }
        )

    return rows


def arg_parser():
    parser = argparse.ArgumentParser(
        description=("Extract Reprojection camera intrinsics from calibration " "TOML files.")
    )
    parser.add_argument(
        "reprojection_directory",
        type=Path,
        help="Directory containing Reprojection calibration TOML files.",
    )
    parser.add_argument(
        "output_csv",
        type=Path,
        help="CSV file to create.",
    )

    return parser.parse_args()


def main():
    args = arg_parser()

    calibration_files = collect_calibration_files(args.reprojection_directory)

    rows = []
    for path in calibration_files:
        rows.extend(parse_calibration(load_calibration(path)))

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)

    with args.output_csv.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=rows[0].keys(),
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} calibration results to " f"{args.output_csv}")


if __name__ == "__main__":
    main()
