#!/bin/bash
# Retriever: HIPPOCAMPUS (the paper's method, reference configuration).
# Contract for every script in scripts/retrievers/:
#   bash scripts/retrievers/<name>.sh <memory_input.json> <results.jsonl>
# The input holds conversations (memory entries) and label-free questions;
# write one JSON row per question: {"question_id", "retrieved_entry_ids"}.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
python method/hippocampus.py --input "$1" --output "$2" \
  --dimension 512 --signature-bits 32 --radius 8 --window 1 --query-window 0 \
  --seed 13 --top-k 10
