#!/bin/bash

set -eou pipefail

# TODO(Jack): Add script dir automatic ID so we can run this from any directory.

# Remove old volumes so we can populate a new one with fresh calibration results
docker compose --env-file ./compose.benchmark.env --file compose.benchmark.yaml \
  down --volumes --remove-orphans

docker compose --env-file ./compose.benchmark.env --file compose.benchmark.yaml \
    up --build