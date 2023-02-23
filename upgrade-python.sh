#!/bin/bash
set -euxo pipefail

pip install pip-tools
pip-compile --upgrade --resolver=backtracking requirements.in
