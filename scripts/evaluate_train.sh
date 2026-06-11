#!/bin/bash
# Evaluate the visible train slice of retrieval artifacts.
#
# Contract mirrors scripts/evaluate.sh:
#   bash scripts/evaluate_train.sh outputs/method_a/retrieval_results.jsonl ...
#
# With no artifact arguments, all outputs/*/retrieval_results.jsonl files are
# scored. The script writes scoring/scores_train.json.

set -euo pipefail

cd /home/user

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

python eval/train/evaluate_retrieval.py \
  --artifacts "${ARTIFACTS[@]}" \
  --output scoring/scores_train.json
