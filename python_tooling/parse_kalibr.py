import argparse
import csv
from pathlib import Path

import yaml
from scipy.spatial.transform import Rotation

CAMCHAIN_SUFFIX = "-camchain.yaml"
IMUCAM_SUFFIX = "-camchain-imucam.yaml"


def collect_camchain_files(kalibr_directory):
    kalibr_directory = Path(kalibr_directory)

    camchain_files = sorted(kalibr_directory.glob(f"*/*{CAMCHAIN_SUFFIX}"))

    if not camchain_files:
        raise RuntimeError(f"No camchain YAML files found under {kalibr_directory}")

    return camchain_files


def collect_imucam_files(kalibr_directory):
    kalibr_directory = Path(kalibr_directory)

    imucam_files = sorted(kalibr_directory.glob(f"*/*{IMUCAM_SUFFIX}"))

    if not imucam_files:
        raise RuntimeError(f"No IMU-camera YAML files found under {kalibr_directory}")

    return imucam_files


def load_camchain(path):
    path = Path(path)

    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict) or len(data) != 1:
        raise ValueError(f"Expected exactly one camera in {path}")

    return data, path


# WARN(Jack): Camera only and also hardcoded only for doublesphere!
def parse_camchain(input):
    data, path = input
    path = Path(path)

    sensor, camera = next(iter(data.items()))

    intrinsics = camera["intrinsics"]
    resolution = camera["resolution"]

    if len(intrinsics) != 6:
        raise ValueError(f"Expected 6 double-sphere intrinsics in {path}, " f"but found {len(intrinsics)}")

    xi, alpha, fx, fy, cx, cy = intrinsics
    width, height = resolution

    # NOTE(Jack): See the camera_model_map in config/business_logic.json for the list of acceptable camera model names
    # and formatting.
    camera_model = f"{camera['camera_model']}-{camera['distortion_model']}"

    return {
        "bag": path.name.removesuffix(CAMCHAIN_SUFFIX),
        "sensor_directory": path.parent.name,
        "sensor_name": camera["rostopic"],
        "camera_model": camera_model,
        "fx": fx,
        "fy": fy,
        "cx": cx,
        "cy": cy,
        "xi": xi,
        "alpha": alpha,
        "width": width,
        "height": height,
        "source_file": str(path),
    }


def parse_imucam(input):
    data, path = input
    path = Path(path)

    sensor, camera = next(iter(data.items()))

    transform = camera["T_cam_imu"]

    if len(transform) != 4 or any(len(row) != 4 for row in transform):
        raise ValueError(f"Expected a 4x4 T_cam_imu transform in {path}")

    tx = transform[0][3]
    ty = transform[1][3]
    tz = transform[2][3]

    rotation_matrix = [
        transform[0][:3],
        transform[1][:3],
        transform[2][:3],
    ]
    qx, qy, qz, qw = Rotation.from_matrix(rotation_matrix).as_quat()

    return {
        "bag": path.name.removesuffix(IMUCAM_SUFFIX),
        "frame_a": "/imu0",
        "frame_b": camera["rostopic"],
        "tx": tx,
        "ty": ty,
        "tz": tz,
        "qx": qx,
        "qy": qy,
        "qz": qz,
        "qw": qw,
        "source_file": str(path),
    }


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def arg_parser():
    parser = argparse.ArgumentParser(description="Extract Kalibr calibration results from camchain YAML files.")
    parser.add_argument(
        "kalibr_directory",
        type=Path,
        help="Directory containing Kalibr camera result directories.",
    )
    parser.add_argument(
        "output_intrinsics_csv",
        type=Path,
    )
    parser.add_argument(
        "output_extrinsics_csv",
        type=Path,
    )

    return parser.parse_args()


def main():
    args = arg_parser()

    camchain_files = collect_camchain_files(args.kalibr_directory)
    imucam_files = collect_imucam_files(args.kalibr_directory)

    intrinsic_rows = [parse_camchain(load_camchain(path)) for path in camchain_files]
    extrinsic_rows = [parse_imucam(load_camchain(path)) for path in imucam_files]

    write_csv(args.output_intrinsics_csv, intrinsic_rows)
    write_csv(args.output_extrinsics_csv, extrinsic_rows)

    print(f"Wrote {len(intrinsic_rows)} intrinsic calibration results to {args.output_intrinsics_csv}")
    print(f"Wrote {len(extrinsic_rows)} extrinsic calibration results to {args.output_extrinsics_csv}")


if __name__ == "__main__":
    main()
