#!/bin/bash

set -eoux pipefail

set +u
source /opt/ros/noetic/setup.bash
set -u

# TODO(Jack): Updating and installing each to time we run the script is not so clean but I don't want to go change
# the kalibr image itself.
apt-get update
apt-get install --no-install-recommends --yes \
    jq
rm --force --recursive /var/lib/apt/lists/*

# NOTE(Jack): Iteration logic adopted from https://stackoverflow.com/questions/68121082/how-to-iterate-over-json-array-with-jq
while read bag_i; do
    # NOTE(Jack): This removes the json quotes
    bag_i=$(echo "${bag_i}" | jq -r ".")

    while read camera_i; do
        camera_i=$(echo "${camera_i}" | jq -r ".")
        camera_name="${camera_i#/}"
        camera_name="${camera_name//\//_}"


        # Unlike Kalibr the sensor name is inside the config file which means we need to pick the right one.
        config_file="/mount/config/reprojection/${camera_name}_config.toml"
        [[ -f "${config_file}" ]] || { echo "Error: camera configuration file does not exist: ${config_file}" >&2; exit 1; }


        /buildroot/reprojection-calibration-application \
          --data "${BENCHMARKING_DATA_INPUT_DIR}/${bag_i}" \
          --config ${config_file} \
          --workspace "${BENCHMARKING_DATA_INPUT_DIR}/reprojection_dbs"


    done < <(jq ".cameras[]" "${DATASET_SPECIFICATION_JSON}")
done < <(jq ".bags[]" "${DATASET_SPECIFICATION_JSON}")
