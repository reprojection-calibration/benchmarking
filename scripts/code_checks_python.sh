#!/bin/bash

set -eoux pipefail

black --version

black --check --diff --verbose '/python_tooling'
isort --check '/python_tooling'