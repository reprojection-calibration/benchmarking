#!/bin/bash

set -eoux pipefail

apt-get update
apt-get install --no-install-recommends --yes \
    ca-certificates \
    wget
rm --force --recursive /var/lib/apt/lists/*

# NOTE(Jack): Putting all the datasets here in one script means we might bust a relatively large cache if anything
# changes - but 4GB of downloads should be ok for anyone with modern internet to have to redownload if need be :)
readonly base_url="https://vision.in.tum.de/tumvi/calibrated/512_16"
readonly -a datasets=(
    "dataset-calib-imu1_512_16.bag"
    "dataset-calib-imu2_512_16.bag"
    "dataset-calib-imu3_512_16.bag"
    "dataset-calib-imu4_512_16.bag"
)

readonly data_dir="/data"
mkdir --parents "${data_dir}"

for dataset in "${datasets[@]}"; do
    wget \
      --directory-prefix="${data_dir}" \
      --progress=bar:force:noscroll \
      --show-progress \
      "${base_url}/${dataset}"
done