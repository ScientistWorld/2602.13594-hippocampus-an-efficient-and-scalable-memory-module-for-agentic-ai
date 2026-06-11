#!/bin/bash
# Evaluate the held-out test slice of retrieval artifacts.
#
# Contract mirrors scripts/evaluate.sh:
#   bash scripts/evaluate_test.sh outputs/method_a/retrieval_results.jsonl ...
#
# With no artifact arguments, all outputs/*/retrieval_results.jsonl files are
# considered. If scoring/scores_train.json exists, the test evaluator scores
# exactly the method entries found there. The script writes scoring/scores_test.json.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p scoring

if [ "$#" -eq 0 ]; then
  mapfile -t ARTIFACTS < <(find outputs -mindepth 2 -maxdepth 2 -name retrieval_results.jsonl -type f | sort)
else
  ARTIFACTS=("$@")
fi

if [ "${#ARTIFACTS[@]}" -eq 0 ]; then
  echo "No retrieval artifacts found under outputs/*/retrieval_results.jsonl" >&2
  exit 1
fi

python eval/test/evaluate_retrieval.py \
  --artifacts "${ARTIFACTS[@]}" \
  --train-scores scoring/scores_train.json \
  --output scoring/scores_test.json
