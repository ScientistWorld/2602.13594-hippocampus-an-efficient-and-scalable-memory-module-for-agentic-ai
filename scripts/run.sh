#!/bin/bash
# Run the core HIPPOCAMPUS reproduction and validation workflow.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

set -euo pipefail

python method/wavelet_selftest.py
bash scripts/reproduce.sh
python validate.py --compare

# Keep the ResearchGym train/test split scores current after reproducing the
# method artifacts.
bash scripts/evaluate_train.sh
bash scripts/evaluate_test.sh
