FROM ubuntu:24.04@sha256:186072bba1b2f436cbb91ef2567abca677337cfc786c86e107d25b7072feef0c AS test-data-download-stage

ARG DOWNLOAD_TEST_DATA=scripts/download_test_data.sh
RUN --mount=type=bind,source=${DOWNLOAD_TEST_DATA},target=/temporary/${DOWNLOAD_TEST_DATA} \
    /temporary/${DOWNLOAD_TEST_DATA}

FROM python:3.12-slim@sha256:3d5ed973e45820f5ba5e46bd065bd88b3a504ff0724d85980dcd05eab361fcf4 AS python-tooling-stage

RUN pip install black isort PyYAML

# NOTE(Jack): We copy the code directly in because we don't want to have to mount the code when we use this in CI
COPY python_tooling/ python_tooling/

ARG CODE_CHECKS_PYTHON=scripts/code_checks_python.sh
RUN --mount=type=bind,source=${CODE_CHECKS_PYTHON},target=/temporary/${CODE_CHECKS_PYTHON} \
    /temporary/${CODE_CHECKS_PYTHON}

RUN python3 -m unittest discover --start-directory /python_tooling/ --verbose
