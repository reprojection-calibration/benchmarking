#!/bin/bash

set -eou pipefail

# TODO(Jack): Is this  script a local script or not? I mean it needs access to the script_folder to mount the entrpoint
# so it is not 100% clear how we should split these scripts up based on use/access. Think about it!


script_folder="$(dirname "$(realpath -s "$0")")"
dataset_specification_json="${script_folder}/../../config/dataset_specification.json"
target_config="${script_folder}/../../config/kalibr/april_6x6_80x80cm.yaml"
target_config="$(realpath -s "${target_config}")"

[[ -f "${dataset_specification_json}" ]] || { echo "Error: json dataset specification does not exist: ${dataset_specification_json}" >&2; exit 1; }
[[ -f "${target_config}" ]] || { echo "Error: Kalibr target configuration does not exist: ${target_config}" >&2; exit 1; }

# NOTE(Jack): Iteration logic adopted from https://stackoverflow.com/questions/68121082/how-to-iterate-over-json-array-with-jq
while read bag_i; do
    # NOTE(Jack): This removes the json quotes
    bag_i=$(echo "${bag_i}" | jq -r ".")

    docker run --rm \
      --entrypoint "/temporary/kalibr_entrypoint.sh" \
      --mount "type=bind,source=${script_folder}/kalibr_entrypoint.sh,target=/temporary/kalibr_entrypoint.sh,readonly" \
      --mount "type=bind,source=${target_config},target=/temporary${target_config},readonly" \
      --mount "type=volume,source=benchmarking-data,target=/data,readonly" \
      --mount "type=volume,source=benchmarking-results,target=/results" \
      kalibr:latest \
      rosrun kalibr kalibr_calibrate_cameras \
        --bag "/data/${bag_i}" \
        --topics /cam0/image_raw \
        --models ds-none \
        --target "/temporary${target_config}"

done < <(jq ".bags.[]" "${dataset_specification_json}")