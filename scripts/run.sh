#!/bin/bash
# Reproduce the reference and registered baselines end to end.
# Optional full audit: python redteam/hardening/run_hardening.py (after this run).
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
if [ -f eval/test/verify_contract.py ]; then
  python eval/test/verify_contract.py
fi
bash scripts/reproduce.sh
python validate.py --compare
