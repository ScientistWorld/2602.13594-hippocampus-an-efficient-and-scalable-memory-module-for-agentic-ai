#!/bin/bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
python redteam/audit.py --case shortcut_wrong_ids_answer_text
