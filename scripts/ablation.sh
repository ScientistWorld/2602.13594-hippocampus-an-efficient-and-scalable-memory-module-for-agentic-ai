#!/bin/bash
# Optional ablation runner for non-scored HIPPOCAMPUS settings.
#
# The standard gym score is produced by scripts/reproduce.sh and must remain
# aligned with scoring/reference.json. This script writes a separate score file
# under tmp/ so additional settings can be inspected without changing the
# paper-reference contract.

set -e

cd /home/user

bash scripts/download.sh

mkdir -p outputs tmp
python method/hippocampus.py \
  --data data/memory_qa.json \
  --output-dir outputs/hippocampus_compact_signature \
  --method-name hippocampus_compact_signature \
  --dimension 512 \
  --signature-bits 16 \
  --radius 3 \
  --window 2 \
  --top-k 3

python eval/evaluate_retrieval.py \
  --artifacts outputs/hippocampus_compact_signature/retrieval_results.jsonl \
  --output tmp/ablation_scores.json

cat tmp/ablation_scores.json
