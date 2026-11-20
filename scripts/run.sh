#!/bin/bash
# Reproduce the reference end to end (CPU only, a few minutes on one core):
# data check, DWM self-test, HIPPOCAMPUS + baselines on train and on the hidden
# test (private questions), run alone so the stored scores come from an
# unshared run. Then the hardening audit (variants + shortcut submissions),
# which writes only under redteam/hardening/results/, and finally validation.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
bash scripts/reproduce.sh
python redteam/hardening/run_hardening.py
python validate.py --compare
