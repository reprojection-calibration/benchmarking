#!/bin/bash

set -eou pipefail

no_cache=()
# TODO(Jack): What should the default stage be? Should there be one?
stage="unset"

for i in "$@"; do
  case "${i}" in
    --no-cache)
      no_cache=("--no-cache")
      shift
      ;;
    --stage)
      stage="${2}"
      shift 2
      ;;
    -*)
      echo "Unknown option $i"
      exit 1;
      ;;
    *)
      ;;
  esac
done

image=benchmarking
script_folder="$(dirname "$(realpath -s "$0")")"
tag=${image}:${stage}

echo "Building image with tag '$tag' targeting stage '$stage'..."
DOCKER_BUILDKIT=1 docker build \
    "${no_cache[@]}" \
    --file "${script_folder}"/../Dockerfile \
    --tag "${tag}" \
    --target "${stage}"-stage \
    --progress=plain \
    "${script_folder}"/../

BUILD_SUCCESSFUL=$?

if [ ${BUILD_SUCCESSFUL} -eq 0 ]; then
    echo "Build successful: ${tag}"
else
    echo "Build failed"
    exit 1
fi