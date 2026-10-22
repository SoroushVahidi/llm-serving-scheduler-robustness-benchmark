#!/usr/bin/env bash
set -euo pipefail
bash paper/tompecs-m2/scripts/build.sh revised manuscript
bash paper/tompecs-m2/scripts/build.sh revised acmsmall
python paper/tompecs-m2/scripts/validate.py
