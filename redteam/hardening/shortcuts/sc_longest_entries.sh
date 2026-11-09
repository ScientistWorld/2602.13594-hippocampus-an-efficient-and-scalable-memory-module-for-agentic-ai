#!/bin/bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../../.."
python redteam/hardening/shortcuts.py longest_entries "$1" "$2"
