#!/bin/bash

set -eoux pipefail

apt-get update
apt-get install --no-install-recommends --yes \
    ca-certificates \
    wget
rm --force --recursive /var/lib/apt/lists/*

# TODO(Jack): But the entire download of all four datasets into one bash script limits the usefulness of caching. Is
# there  way to structure this that would allow us to better make use of caching? Honestly this script should never
# change so I guess we should never need that.
declare -a datasets=("dataset-calib-imu1_512_16.bag" "dataset-calib-imu2_512_16.bag" "dataset-calib-imu3_512_16.bag" "dataset-calib-imu4_512_16.bag")

for dataset in "${datasets[@]}"
do
   wget \
     --directory-prefix="/data" \
     --progress=bar:force:noscroll \
     --show-progress \
     "https://vision.in.tum.de/tumvi/calibrated/512_16/${dataset}"
done

