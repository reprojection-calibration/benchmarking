#!/bin/bash

set -eoux pipefail

# TODO(Jack): Make this a default value but let the user set it via an env var!
script_folder="$(dirname "$(realpath -s "$0")")"
THIRDPARTY_DIR="${script_folder}/../../thirdparty"

apt-get update
apt-get install --no-install-recommends --yes \
    git
rm --force --recursive /var/lib/apt/lists/*

if [[ -n "${SUDO_USER:-}" ]]; then
    sudo -u "${SUDO_USER}" git clone \
        "https://github.com/ethz-asl/kalibr.git" "${THIRDPARTY_DIR}/kalibr"
else
    git clone "https://github.com/ethz-asl/kalibr.git" "${THIRDPARTY_DIR}/kalibr"
fi