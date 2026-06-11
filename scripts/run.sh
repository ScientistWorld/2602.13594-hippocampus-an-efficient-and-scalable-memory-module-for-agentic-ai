#!/bin/bash
# Score the visible train and held-out test evaluation slices over existing
# retrieval artifacts. Do not regenerate method outputs in this designer pass.

cd /home/user

set -euo pipefail

bash scripts/evaluate_train.sh
bash scripts/evaluate_test.sh
python validate.py --reference-only
