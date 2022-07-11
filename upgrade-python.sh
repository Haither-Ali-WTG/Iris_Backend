#!/bin/bash
set -euxo pipefail

pip install pip-tools
pip-compile --upgrade requirements.in
