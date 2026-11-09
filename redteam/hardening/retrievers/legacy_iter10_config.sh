#!/bin/bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../../.."
python method/hippocampus.py --input "$1" --output "$2" --dimension 512 --signature-bits 32 --radius 7 --window 2 --query-window 1 --seed 13 --top-k 10 --hyperplanes sparse --scoring position_sum
