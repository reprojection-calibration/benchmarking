#!/bin/bash

set -eoux pipefail

# WARN(Jack): This script requires that you have git and docker installed! The best way to manage that at this time
# is not clear!

# TODO(Jack): Make this a default value but let the user set it via an env var!
script_folder="$(dirname "$(realpath -s "$0")")"
THIRDPARTY_DIR="${script_folder}/../../thirdparty"

# NOTE(Jack): We need to solve the case where we are running this locally on a users system that needs sudo to
# update/install apt packages, but we do not want the git clone to happen as the super user because that causes
# ownership problems. If sudo is not used (ex. in the gha pipeline) then we can just clone like normal :)
if [[ -n "${SUDO_USER:-}" ]]; then
    sudo --user="${SUDO_USER}" git clone \
        "https://github.com/ethz-asl/kalibr.git" "${THIRDPARTY_DIR}/kalibr"
else
    git clone "https://github.com/ethz-asl/kalibr.git" "${THIRDPARTY_DIR}/kalibr"
fi

docker build \
    --file "${THIRDPARTY_DIR}/kalibr/Dockerfile_ros1_20_04" \
    --tag kalibr \
    "${THIRDPARTY_DIR}/kalibr"
