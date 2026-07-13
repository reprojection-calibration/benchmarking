#!/bin/bash

set -eoux pipefail

# NOTE(Jack): These three lines are the classic lines found in the Kalibr dockerfile entrypoint
export KALIBR_MANUAL_FOCAL_LENGTH_INIT=1
set +u; source "${WORKSPACE}/devel/setup.bash"; set -u
cd "${WORKSPACE}"

# TODO(Jack): Updating and installing each to time we run the script is not so clean but I don't want to go change
# the kalibr image itself.
apt-get update
apt-get install --no-install-recommends --yes \
    jq
rm --force --recursive /var/lib/apt/lists/*

# TODO(Jack): Hardcoding these paths here does not seem like an eloquent solution but it is quick, easy, and gets the
# job done!
dataset_specification_json="/temporary/config/dataset_specification.json"
[[ -f "${dataset_specification_json}" ]] || { echo "Error: json dataset specification does not exist: ${dataset_specification_json}" >&2; exit 1; }
target_config="/temporary/config/kalibr/april_6x6_80x80cm.yaml"
[[ -f "${target_config}" ]] || { echo "Error: Kalibr target configuration does not exist: ${target_config}" >&2; exit 1; }

# NOTE(Jack): Iteration logic adopted from https://stackoverflow.com/questions/68121082/how-to-iterate-over-json-array-with-jq
while read bag_i; do
    # NOTE(Jack): This removes the json quotes
    bag_i=$(echo "${bag_i}" | jq -r ".")

    while read camera_i; do
        camera_i=$(echo "${camera_i}" | jq -r ".")

        rosrun kalibr kalibr_calibrate_cameras \
          --bag "/data/${bag_i}" \
          --dont-show-report \
          --models ds-none \
          --target "${target_config}" \
          --topics "${camera_i}"

        # NOTE(Jack): We need to clean the camera name from having slashes (ex. like in a ROS topic) because otherwise
        # the mkdir command below will interpret that as a multilevel path.
        camera_name="${camera_i#/}"
        camera_name="${camera_name//\//_}"

        # NOTE(Jack): Kalibr does not let us specify an output path or filename for the output diagnostics. Therefore
        # we need to manually move all the outputs into a batch specific (i.e. camera name and model) directory.
        mkdir --parents "/data/kalibr/${camera_name}"
        mv -- /data/*.pdf /data/*.txt /data/*.yaml "/data/kalibr/${camera_name}"

    done < <(jq ".cameras[]" "${dataset_specification_json}")
done < <(jq ".bags[]" "${dataset_specification_json}")
