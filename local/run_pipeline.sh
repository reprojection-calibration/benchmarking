#!/bin/bash

set -eou pipefail

docker compose \
    --file compose.benchmark.yaml up \
    --build