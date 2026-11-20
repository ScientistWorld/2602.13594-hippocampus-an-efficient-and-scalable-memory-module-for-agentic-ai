#!/usr/bin/env python3
"""Freeze the final reference from official runs; never invoked by evaluation.

Only setup metadata and reproduced results change. The paper's reported
numbers are copied verbatim and must remain identical.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / 'scoring/reference.json'
reference = json.loads(p.read_text())
exp = reference['experiments']['locomo_memory_retrieval']
paper = exp['_paper_reported']
scores = json.loads((ROOT / 'scoring/scores_test.json').read_text())['experiments']['locomo_memory_retrieval']
if not scores['_status']['hippocampus']['valid']:
    raise SystemExit('Cannot freeze a failed reference')
for name, metrics in scores['results'].items():
    kind = 'proposed' if name == 'hippocampus' else 'baseline'
    exp['results'][name] = {'type': kind, **metrics}
exp['_reference_run_hidden_test'] = {
    'note': 'Final sequential reference run on 659 private questions; raw outputs in eval/test/audit/raw_test; paired audit in redteam/hardening/results/summary.json. No wall-clock limit.',
    'hippocampus': scores['results']['hippocampus'],
    'full_history_context_tokens_per_question': scores['_fixed_comparisons']['full_history_context_tokens'],
}
assert exp['_paper_reported'] == paper
p.write_text(json.dumps(reference, indent=2) + '\n')
print('Froze all scored metrics from the official reference run; paper numbers unchanged.')
