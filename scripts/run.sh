#!/bin/bash
# Reference reproduction + hardening verification (CPU only).
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# 1. Reference end to end: data check, DWM self-test, every registered
#    retriever (HIPPOCAMPUS + baselines) on train and on the hidden test.
bash scripts/reproduce.sh

# 2. Hardening check: seeds, better/weaker variants and shortcut submissions
#    through the hidden test (results in redteam/hardening/results/).
python redteam/hardening/run_hardening.py

python validate.py --compare || true
