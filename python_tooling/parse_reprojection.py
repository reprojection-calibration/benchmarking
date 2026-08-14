import argparse
import csv
import tomllib
from pathlib import Path

from scipy.spatial.transform import Rotation

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


def parse_intrinsic_calibration(
    workflow_name,
    table_id,
    camera,
    path,
):
    intrinsics = camera["intrinsics"]
    resolution = camera["resolution"]

    if len(intrinsics) != 5:
        raise ValueError(
            f"Expected 5 double-sphere intrinsics for "
            f"'{workflow_name}.{table_id}' in {path}, "
            f"but found {len(intrinsics)}"
        )

    if len(resolution) != 2:
        raise ValueError(
            f"Expected a two-element resolution for "
            f"'{workflow_name}.{table_id}' in {path}, "
            f"but found {len(resolution)}"
        )

    focal_length, cx, cy, xi, alpha = intrinsics
    width, height = resolution

    return {
        "bag": path.name.removesuffix(CALIBRATION_SUFFIX),
        "table_id": table_id,
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


def parse_extrinsic_calibration(
    workflow_name,
    table_id,
    extrinsic,
    path,
):
    transform = extrinsic["tf_a_b"]

    if len(transform) != 4 or any(len(row) != 4 for row in transform):
        raise ValueError(f"Expected a 4x4 transform for " f"'{workflow_name}.{table_id}' in {path}")

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
        "bag": path.name.removesuffix(CALIBRATION_SUFFIX),
        "table_id": table_id,
        "frame_a": extrinsic["frame_a"],
        "frame_b": extrinsic["frame_b"],
        "tx": tx,
        "ty": ty,
        "tz": tz,
        "qx": qx,
        "qy": qy,
        "qz": qz,
        "qw": qw,
        "source_file": str(path),
    }


# WARN(Jack): Camera only and hardcoded for the double-sphere model.
def parse_calibration(input):
    data, path = input
    path = Path(path)

    intrinsic_rows = []
    extrinsic_rows = []

    for workflow_name, workflow in data.items():
        for name, calibration in workflow.items():
            if not isinstance(calibration, dict):
                continue

            if name.startswith("cam"):
                intrinsic_rows.append(parse_intrinsic_calibration(workflow_name, name, calibration, path))
            elif name.startswith("extrinsic"):
                extrinsic_rows.append(
                    parse_extrinsic_calibration(
                        workflow_name,
                        name,
                        calibration,
                        path,
                    )
                )

    return intrinsic_rows, extrinsic_rows


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
        "--output-intrinsics-csv",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--output-extrinsics-csv",
        type=Path,
        required=True,
    )

    return parser.parse_args()


def write_csv(path, rows):
    if not rows:
        return

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def main():
    args = arg_parser()

    calibration_files = collect_calibration_files(args.reprojection_directory)

    intrinsic_rows = []
    extrinsic_rows = []

    for path in calibration_files:
        intrinsics, extrinsics = parse_calibration(load_calibration(path))
        intrinsic_rows.extend(intrinsics)
        extrinsic_rows.extend(extrinsics)

    write_csv(args.output_intrinsics_csv, intrinsic_rows)
    write_csv(args.output_extrinsics_csv, extrinsic_rows)

    print(f"Wrote {len(intrinsic_rows)} intrinsic calibration results to " f"{args.output_intrinsics_csv}")
    print(f"Wrote {len(extrinsic_rows)} extrinsic calibration results to " f"{args.output_extrinsics_csv}")


if __name__ == "__main__":
    main()
