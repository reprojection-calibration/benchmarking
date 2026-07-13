#!/bin/bash

set -eox pipefail

export KALIBR_MANUAL_FOCAL_LENGTH_INIT=1
source "${WORKSPACE}/devel/setup.bash"
cd "${WORKSPACE}"

exec "$@"