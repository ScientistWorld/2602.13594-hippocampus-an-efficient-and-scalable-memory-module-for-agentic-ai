#!/bin/bash
# Final reference end to end, followed by the single sequential hardening audit.
# No installs, downloads, parallel retrievers or wall-clock limits in this job.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
python eval/test/verify_contract.py
bash scripts/reproduce.sh
python redteam/hardening/run_hardening.py
python scripts/freeze_reference.py
python validate.py --compare
