#!/bin/bash

set -eoux pipefail

black --version

black --check --diff  --line-length 120 --verbose '/python_tooling'
isort --check '/python_tooling'