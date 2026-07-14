#!/bin/bash

set -eoux pipefail

black --version

black --check --diff --verbose '/temporary/python_tooling'
isort --check '/temporary/python_tooling'