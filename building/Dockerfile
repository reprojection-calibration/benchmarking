FROM ubuntu:24.04@sha256:186072bba1b2f436cbb91ef2567abca677337cfc786c86e107d25b7072feef0c AS test-data-download-stage

ARG DOWNLOAD_TEST_DATA=scripts/download_test_data.sh
RUN --mount=type=bind,source=${DOWNLOAD_TEST_DATA},target=/temporary/${DOWNLOAD_TEST_DATA} \
    /temporary/${DOWNLOAD_TEST_DATA}