#!/bin/bash

set -eoux pipefail

black --check --verbose '/temporary/python_tooling'
isort --check '/temporary/python_tooling'