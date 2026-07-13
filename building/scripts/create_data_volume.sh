#!/bin/bash

set -eoux pipefail

# TODO(Jack): How should we actually use volumes in the workflow?

docker volume create benchmarking-data
docker run --rm \
  --volume benchmarking-data:/volume/data \
  benchmarking:test-data-download \
  cp --recursive /data /volume/data
