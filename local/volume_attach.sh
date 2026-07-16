#!/bin/bash

set -eou pipefail

volume="benchmarking-results"

for i in "$@"; do
  case "${i}" in
    --volume)
      volume="${2}"
      shift 2
      ;;
    -*)
      echo "Unknown option $i"
      exit 1;
      ;;
    *)
      ;;
  esac
done

docker run \
  --interactive \
  --mount type=volume,source=${volume},target=/data \
  --rm \
  --tty \
  ubuntu:24.04 bash