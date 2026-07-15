#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import sqlite3
import sys
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = {
    "dataset",
    "sensor_name",
    "camera_info_key",
    "feature_extraction_key",
}

EMPTY_INPUT_CACHE_KEY = hashlib.sha256(b"").hexdigest()

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS entity
(
    entity_id   TEXT     NOT NULL,
    entity_type TEXT     NOT NULL CHECK (entity_type IN ('camera',
                                                         'extrinsic',
                                                         'imu',
                                                         'target')),
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (entity_id)
);

CREATE TABLE IF NOT EXISTS calibration_steps
(
    step_name  TEXT     NOT NULL CHECK (step_name IN ('bundle_adjustment',
                                                      'camera_info',
                                                      'extrinsic_initialization',
                                                      'extrinsic_optimization',
                                                      'feature_extraction',
                                                      'image_loading',
                                                      'imu_data_loading',
                                                      'intrinsic_initialization',
                                                      'pose_initialization',
                                                      'spline_initialization',
                                                      'target_info')),
    entity_id  TEXT     NOT NULL,
    cache_key  TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (entity_id) REFERENCES entity ON DELETE CASCADE,
    PRIMARY KEY (step_name, entity_id)
);

CREATE TABLE IF NOT EXISTS camera_info
(
    step_name    TEXT        NOT NULL CHECK (step_name IN ('camera_info')),
    sensor_name  TEXT UNIQUE NOT NULL,
    camera_model TEXT        NOT NULL CHECK (camera_model IN
                                             ('double_sphere',
                                              'pinhole',
                                              'pinhole_radtan4',
                                              'unified_camera_model')),
    height       INTEGER     NOT NULL,
    width        INTEGER     NOT NULL,

    FOREIGN KEY (step_name, sensor_name)
        REFERENCES calibration_steps (step_name, entity_id)
        ON DELETE CASCADE,
    PRIMARY KEY (sensor_name, camera_model)
);
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Update Reprojection calibration databases so camera-info and "
            "feature-extraction steps produce cache hits."
        )
    )
    parser.add_argument(
        "database_directory",
        type=Path,
        help="Directory containing *.calib.db3 databases.",
    )
    parser.add_argument(
        "cache_keys_csv",
        type=Path,
        help="CSV containing dataset, sensor_name, camera_info_key, and feature_extraction_key.",
    )
    parser.add_argument(
        "--camera-model",
        default="double_sphere",
        choices=(
            "double_sphere",
            "pinhole",
            "pinhole_radtan4",
            "unified_camera_model",
        ),
        help="Camera model written to camera_info (default: double_sphere).",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=512,
        help="Camera image width written to camera_info (default: 512).",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=512,
        help="Camera image height written to camera_info (default: 512).",
    )
    return parser.parse_args()


def load_cache_keys(csv_path: Path) -> pd.DataFrame:
    if not csv_path.is_file():
        raise FileNotFoundError(f"Cache-key CSV does not exist: {csv_path}")

    dataframe = pd.read_csv(csv_path, dtype=str, keep_default_na=False)

    missing_columns = REQUIRED_COLUMNS - set(dataframe.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"{csv_path}: missing required columns: {missing}")

    dataframe = dataframe[
        [
            "dataset",
            "sensor_name",
            "camera_info_key",
            "feature_extraction_key",
        ]
    ].copy()

    for column in dataframe.columns:
        dataframe[column] = dataframe[column].str.strip()

    if dataframe.empty:
        raise ValueError(f"{csv_path}: contains no cache-key rows")

    empty_fields = dataframe.eq("")
    if empty_fields.any().any():
        row_index, column_index = next(zip(*empty_fields.to_numpy().nonzero()))
        column = dataframe.columns[column_index]
        csv_row = row_index + 2
        raise ValueError(f"{csv_path}:{csv_row}: '{column}' is empty")

    duplicates = dataframe.duplicated(
        subset=["dataset", "sensor_name"],
        keep=False,
    )
    if duplicates.any():
        duplicate_rows = dataframe.loc[duplicates, ["dataset", "sensor_name"]].drop_duplicates()
        values = ", ".join(f"({row.dataset}, {row.sensor_name})" for row in duplicate_rows.itertuples(index=False))
        raise ValueError("Duplicate dataset/sensor_name combinations in CSV: " + values)

    for column in ("camera_info_key", "feature_extraction_key"):
        invalid = ~dataframe[column].str.fullmatch(r"[0-9a-fA-F]{64}")
        if invalid.any():
            row_index = dataframe.index[invalid][0]
            csv_row = int(row_index) + 2
            value = dataframe.at[row_index, column]
            raise ValueError(
                f"{csv_path}:{csv_row}: '{column}' is not a 64-character " f"SHA-256 hexadecimal value: {value!r}"
            )
        dataframe[column] = dataframe[column].str.lower()

    return dataframe


def dataset_name_from_database(database_path: Path) -> str:
    suffix = ".calib.db3"
    if not database_path.name.endswith(suffix):
        raise ValueError(f"Unexpected database filename (expected '*{suffix}'): " f"{database_path.name}")
    return database_path.name[: -len(suffix)]


def create_required_tables(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_SQL)


def upsert_camera_cache_state(
    connection: sqlite3.Connection,
    *,
    sensor_name: str,
    camera_info_key: str,
    feature_extraction_key: str,
    camera_model: str,
    width: int,
    height: int,
) -> None:
    connection.execute(
        """
        INSERT INTO entity (entity_id, entity_type)
        VALUES (?, 'camera')
        ON CONFLICT(entity_id) DO UPDATE SET
            entity_type = excluded.entity_type
        """,
        (sensor_name,),
    )

    for step_name, cache_key in (
        ("image_loading", EMPTY_INPUT_CACHE_KEY),
        ("camera_info", camera_info_key),
        ("feature_extraction", feature_extraction_key),
    ):
        connection.execute(
            """
            INSERT INTO calibration_steps (step_name, entity_id, cache_key)
            VALUES (?, ?, ?)
            ON CONFLICT(step_name, entity_id) DO UPDATE SET
                cache_key = excluded.cache_key
            """,
            (step_name, sensor_name, cache_key),
        )

    connection.execute(
        """
        INSERT INTO camera_info (
            step_name,
            sensor_name,
            camera_model,
            height,
            width
        )
        VALUES ('camera_info', ?, ?, ?, ?)
        ON CONFLICT(sensor_name) DO UPDATE SET
            step_name = excluded.step_name,
            camera_model = excluded.camera_model,
            height = excluded.height,
            width = excluded.width
        """,
        (sensor_name, camera_model, height, width),
    )


def process_database(
    database_path: Path,
    rows: pd.DataFrame,
    *,
    camera_model: str,
    width: int,
    height: int,
) -> int:
    connection = sqlite3.connect(database_path)

    try:
        connection.execute("PRAGMA foreign_keys = ON")

        with connection:
            create_required_tables(connection)

            for row in rows.itertuples(index=False):
                upsert_camera_cache_state(
                    connection,
                    sensor_name=row.sensor_name,
                    camera_info_key=row.camera_info_key,
                    feature_extraction_key=row.feature_extraction_key,
                    camera_model=camera_model,
                    width=width,
                    height=height,
                )
    finally:
        connection.close()

    return len(rows)


def main() -> int:
    args = parse_args()

    if not args.database_directory.is_dir():
        raise NotADirectoryError(f"Database directory does not exist: {args.database_directory}")

    if args.width <= 0 or args.height <= 0:
        raise ValueError("--width and --height must both be positive")

    cache_keys = load_cache_keys(args.cache_keys_csv)
    database_paths = sorted(args.database_directory.glob("*.calib.db3"))

    if not database_paths:
        raise FileNotFoundError(f"No '*.calib.db3' databases found in " f"{args.database_directory}")

    processed_datasets: set[str] = set()
    total_cameras = 0

    for database_path in database_paths:
        dataset = dataset_name_from_database(database_path)
        rows = cache_keys.loc[cache_keys["dataset"] == dataset]

        if rows.empty:
            raise ValueError(f"No cache keys found for database dataset '{dataset}'")

        camera_count = process_database(
            database_path,
            rows,
            camera_model=args.camera_model,
            width=args.width,
            height=args.height,
        )

        processed_datasets.add(dataset)
        total_cameras += camera_count
        print(f"Updated {database_path.name}: " f"{camera_count} camera(s)")

    unused_datasets = sorted(set(cache_keys["dataset"]) - processed_datasets)
    if unused_datasets:
        print(
            "Warning: CSV rows were not used because no matching database " f"was found: {', '.join(unused_datasets)}",
            file=sys.stderr,
        )

    print(f"Finished: updated {len(database_paths)} database(s) and " f"{total_cameras} camera cache state(s).")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, NotADirectoryError, ValueError, sqlite3.Error) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1)
