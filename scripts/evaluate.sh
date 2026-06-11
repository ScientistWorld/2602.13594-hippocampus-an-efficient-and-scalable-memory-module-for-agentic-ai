#!/bin/bash
# Evaluation script — the standard way to evaluate work in this environment.
#
# This script must be SELF-CONTAINED using only code in eval/.
# Do NOT import from method/ — evaluate.sh must work even when the
# paper's method code is hidden from a scientist agent.
#
# Design it so that anyone following the same output format can run
# this script to evaluate their results.
#
# OUTPUT CONTRACT: This script MUST write scoring/scores.json containing
# a JSON dict nested by experiment, e.g.:
#   {"imagenet_classification": {"top1_accuracy": 82.1, "top5_accuracy": 94.8}}
# Experiment and metric names must match the keys in scoring/reference.json.
# This file is read by the system for automated comparison.
#
# Example usage:
#   bash scripts/evaluate.sh outputs/hippocampus/retrieval_results.jsonl
#   bash scripts/evaluate.sh outputs/hippocampus/retrieval_results.jsonl outputs/lexical_baseline/retrieval_results.jsonl
#
# Called from run.sh after training, or independently.

set -e

cd /home/user

mkdir -p scoring

if [ "$#" -eq 0 ]; then
  set -- outputs/hippocampus/retrieval_results.jsonl
fi

python eval/evaluate_retrieval.py --artifacts "$@" --output scoring/scores.json
