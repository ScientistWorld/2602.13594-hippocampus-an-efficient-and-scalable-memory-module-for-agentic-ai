#!/usr/bin/env python3
"""Lightweight contract and private-source checks, run before the audit job.

No retriever is trained or run here. Actual malformed-output and disclosure
attacks are separately rerun on all hidden questions by the hardening audit.
"""
import importlib.util
import json
import tempfile
from collections import Counter
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    private = json.loads((HERE / 'private_questions.json').read_text())['questions']
    test = json.loads((HERE / 'locomo_test.json').read_text())
    fields = ('question_id','conversation_id','question','answer','evidence_entry_ids','category')
    assert [{k:q[k] for k in fields} for q in private] == test['questions']
    assert len(private) == 659
    assert Counter(q['category'] for q in private) == {
        'single_hop':307, 'multi_hop':131, 'temporal':163, 'open_domain':58}
    assert all(q.get('support') for q in private), 'Each authored question needs a support check'
    entries = {e['entry_id']:c['conversation_id'] for c in test['conversations'] for e in c['entries']}
    assert all(q['evidence_entry_ids'] and all(entries[e] == q['conversation_id'] for e in q['evidence_entry_ids']) for q in private)
    assert len({q['question_id'] for q in private}) == len(private)
    for split in ('train','test'):
        m = load(ROOT / 'eval' / split / 'evaluate_retrieval.py', f'contract_{split}')
        data = m.load_dataset(m.DATA_PATH)
        worst = m.failed_metrics(data)
        assert set(worst) == set(m.SCORED_METRICS)
        assert all(worst[k] == 0 for k in m.SCORED_METRICS if k != 'avg_context_tokens')
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'output.jsonl'
            for content in (b'\xff', b'{', b'null\n', b'[]\n', b'{}\n', b''):
                p.write_bytes(content)
                try:
                    m.parse_rows(p, data)
                except m.RunFailure:
                    pass
                else:
                    raise AssertionError(f'{split}: malformed artifact accepted')
        # Lack of isolation must fail every method and never invoke it.
        with patch.object(m, 'probe_isolation', return_value=(False, 'denied')), \
             patch.object(m, 'run_retriever') as runner:
            scores = m.evaluate([Path('/fake/any_method.sh')], data, None, None)
            assert not runner.called
            assert scores['experiments'][m.EXPERIMENT]['results']['any_method'] == worst
    print('Private source, split independence, parsing and fail-closed checks passed.')


if __name__ == '__main__':
    main()
