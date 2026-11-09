#!/bin/bash
# Reproduce the reference end to end: data, DWM self-test, every registered
# retriever (HIPPOCAMPUS + baselines) scored on train and on the hidden test.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
bash scripts/download.sh
python method/wavelet_selftest.py
bash scripts/evaluate_train.sh
# scores.json is the visible (train-split) reproduction; same protocol as evaluate.sh.
cp scoring/scores_train.json scoring/scores.json
if [ -d eval/test ]; then
  bash scripts/evaluate_test.sh
fi
