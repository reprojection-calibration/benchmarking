import argparse
import sqlite3
from pathlib import Path

import pandas as pd

SENSOR_ASSET_IDS = {
    "/cam0/image_raw": 1,
    "/cam1/image_raw": 2,
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("database_directory", type=Path)
    parser.add_argument("cache_keys_csv", type=Path)

    return parser.parse_args()


def update_database(db_path, rows):
    with sqlite3.connect(db_path) as db:
        db.execute("PRAGMA foreign_keys = ON")

        for row in rows.itertuples(index=False):
            asset_id = SENSOR_ASSET_IDS[row.sensor_name]

            workflow_id = db.execute(
                """
                SELECT workflow_id
                FROM workflow_assets
                WHERE asset_id = ?
                ORDER BY workflow_id
                LIMIT 1
                """,
                (asset_id,),
            ).fetchone()[0]

            for step_type, cache_key in (
                ("image_loading", row.image_loading_key),
                ("feature_extraction", row.feature_extraction_key),
            ):
                db.execute(
                    """
                    UPDATE steps
                    SET cache_key = ?
                    WHERE id = (SELECT step_id
                                FROM workflow_steps
                                WHERE workflow_id = ?
                                  AND type = ?)
                    """,
                    (
                        cache_key,
                        workflow_id,
                        step_type,
                    ),
                )

            camera_info_step_id = db.execute(
                """
                INSERT INTO steps (type, cache_key)
                VALUES ('camera_info', ?)
                RETURNING id
                """,
                (row.camera_info_key,),
            ).fetchone()[0]

            db.execute(
                """
                INSERT INTO workflow_steps (workflow_id,
                                            type,
                                            step_id)
                VALUES (?, 'camera_info', ?)
                """,
                (
                    workflow_id,
                    camera_info_step_id,
                ),
            )

            # TODO(Jack): Can we use the sql directly from the third party reprojection directory?
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS camera_info
                (
                    step_id      INTEGER NOT NULL,
                    asset_id     INTEGER NOT NULL,
                    camera_model TEXT    NOT NULL CHECK ( camera_model IN
                                                          ('double_sphere', 'pinhole', 'pinhole_radtan4', 'unified_camera_model')),
                    height       INTEGER NOT NULL,
                    width        INTEGER NOT NULL,

                    FOREIGN KEY (step_id) REFERENCES steps (id) ON DELETE CASCADE,
                    FOREIGN KEY (asset_id) REFERENCES assets (id) ON DELETE CASCADE,
                    PRIMARY KEY (step_id, asset_id)
                );
                """,
                ()
            )

            db.execute(
                """
                INSERT INTO camera_info (step_id,
                                         asset_id,
                                         camera_model,
                                         height,
                                         width)
                VALUES (?, ?, 'double_sphere', 512, 512)
                """,
                (
                    camera_info_step_id,
                    asset_id,
                ),
            )


def main():
    args = parse_args()

    cache_keys = pd.read_csv(
        args.cache_keys_csv,
        dtype=str,
    )

    for db_path in sorted(args.database_directory.glob("*.calib.db3")):
        dataset = db_path.name.removesuffix(".calib.db3")

        rows = cache_keys[cache_keys["dataset"] == dataset]

        update_database(db_path, rows)

        print(f"Updated {db_path.name}: " f"{len(rows)} camera(s)")


if __name__ == "__main__":
    main()
