#!/bin/bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../../.."
python redteam/hardening/shortcuts.py prewrite_scores "$1" "$2"
