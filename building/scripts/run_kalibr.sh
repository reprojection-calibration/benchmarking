#!/bin/bash

set -eoux pipefail

# TODO(Jack): Is this  script a local script or not? I mean it needs access to the script_folder to mount the entrpoint
# so it is not 100% clear how we should split these scripts up based on use/access. Think about it!

script_folder="$(dirname "$(realpath -s "$0")")"

docker run --rm \
  --entrypoint "/temporary/kalibr_entrypoint.sh" \
  --mount "type=bind,source=${script_folder}/kalibr_entrypoint.sh,target=/temporary/kalibr_entrypoint.sh" \
  kalibr:latest \
  rosrun kalibr kalibr_calibrate_cameras \
    --bag /data/input.bag \
    --topics /cam0/image_raw \
    --models pinhole-radtan \
    --target /data/target.yaml