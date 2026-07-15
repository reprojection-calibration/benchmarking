## Build

When cloning the repository make sure to get the submodules:

        git clone --recurse-submodules git@github.com:reprojection-calibration/benchmarking.git

Or after you already cloned it but forget the submodules:

        git submodule update --init --recursive


docker run --rm -it --mount "type=bind,source=$(pwd)/thirdparty/kalibr,target=/catkin_ws/src/kalibr,readonly" --mount "type=bind,source=/home/jack/data/TUM-Visual-Inertial-Dataset/,target=/data" --mount "type=bind,source=/home/jack/code/github/reprojection-calibration/benchmarking/config,target=/config,readonly"  kalibr:latest

rosrun kalibr kalibr_calibrate_cameras --bag "/data/dataset-calib-imu1_512_16.bag" --dont-show-report --models ds-none --target /config/kalibr/april_6x6_80x80cm.yaml --topics /cam0/image_raw

timestamp_ns  = obs.time().toNSec()
print("raw:", timestamp_ns)
print("type:", type(timestamp_ns))
print("as Python int:", int(timestamp_ns))
print(timestamp_ns)
pixels = np.asarray(obs.getCornersImageFrame())
points = np.asarray(obs.getCornersTargetFrame())

ids = np.asarray(obs.getCornersIdx()).reshape(-1)
target = obs.target()
grid_indices = np.empty((ids.size, 2), dtype=np.int32)

for index, corner_id in enumerate(ids):
    grid_coordinate = target.pointToGridCoordinates(int(corner_id))

    grid_indices[index, 0] = grid_coordinate[0]
    grid_indices[index, 1] = grid_coordinate[1]

if points.ndim != 2 or points.shape[1] != 3:
    raise ValueError(f"Expected points to have shape (N, 3), got {points.shape}")

if pixels.ndim != 2 or pixels.shape[1] != 2:
    raise ValueError(f"Expected pixels to have shape (N, 2), got {pixels.shape}")

if grid_indices.ndim != 2 or grid_indices.shape[1] != 2:
    raise ValueError(f"Expected grid_indices to have shape (N, 2), got {grid_indices.shape}")

num_observations = points.shape[0]

if pixels.shape[0] != num_observations or ids.size != num_observations:
    raise ValueError(
        "points, pixels and ids contain different numbers of observations: "
        f"points={points.shape[0]}, "
        f"pixels={pixels.shape[0]}, "
        f"ids={ids.size}"
    )

dataframe = pd.DataFrame(
    {
        "id_x": grid_indices[:,0],
        "id_y": grid_indices[:,1],
        "pixel_x": pixels[:, 0],
        "pixel_y": pixels[:, 1],
        "point_x": points[:, 0],
        "point_y": points[:, 1],
        "point_z": points[:, 2],
    }
)

clean_bag_name = Path(parsed.bagfile).stem
safe_topic_name = topic.strip("/").replace("/", "_")
output_directory = Path(f"/data/outputs/{clean_bag_name}/{safe_topic_name}")
output_directory.mkdir(parents=True, exist_ok=True)

output_path = output_directory / f"{timestamp_ns}.csv"

dataframe.to_csv(output_path, index=False)