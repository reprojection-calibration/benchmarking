#!/bin/bash

set -eou pipefail

local_mount=()
# TODO(Jack): What should the default stage be? Should there be one?
stage="unset"

for i in "$@"; do
  case "${i}" in
    --mount-local)
      script_folder="$(dirname "$(realpath -s "$0")")"
      local_mount=("${script_folder}/../../:/temporary")
      shift
      ;;
    --stage)
      stage="${2}"
      shift 2
      ;;
    -*)
      echo "Unknown option $i"
      exit 1
      ;;
    *)
      ;;
  esac
done

image=benchmarking
tag=${image}:${stage}

echo "Running container from image with tag '$tag'..."
docker run \
  --entrypoint="" \
  --interactive \
  --volume "${local_mount[@]}" \
  --rm \
  --tty \
  "${tag}" /bin/bash