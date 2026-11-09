#!/bin/bash
# Reproduce the reference end to end (CPU only, ~5 minutes on one core):
# data check, DWM self-test, HIPPOCAMPUS + baselines on train and hidden test.
# The hardening audit (variants + shortcut submissions) is separate:
#   python redteam/hardening/run_hardening.py
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
bash scripts/reproduce.sh
python validate.py --compare
