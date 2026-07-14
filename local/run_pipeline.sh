#!/bin/bash

set -eou pipefail

# Remove old volumes so we can populate a new one with fresh calibration results
docker compose --file compose.benchmark.yaml \
  down --volumes --remove-orphans

docker compose --file compose.benchmark.yaml \
    up --build