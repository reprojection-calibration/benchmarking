#!/bin/bash

set -eoux pipefail

# TODO(Jack): Make this a default value but let the user set it via an env var!
script_folder="$(dirname "$(realpath -s "$0")")"
THIRDPARTY_DIR="${script_folder}/../../thirdparty"

apt-get update
apt-get install --no-install-recommends --yes \
    git
rm --force --recursive /var/lib/apt/lists/*

# NOTE(Jack): We need to solve the case where we are running this locally on a users system that needs sudo to
# update/install apt packages, but we do not want the git clone to happen as the super user because that causes
# ownership problems. If sudo is not used (ex. in the gha pipeline) then we can just clone like normal :)
if [[ -n "${SUDO_USER:-}" ]]; then
    sudo --user="${SUDO_USER}" git clone \
        "https://github.com/ethz-asl/kalibr.git" "${THIRDPARTY_DIR}/kalibr"
else
    git clone "https://github.com/ethz-asl/kalibr.git" "${THIRDPARTY_DIR}/kalibr"
fi