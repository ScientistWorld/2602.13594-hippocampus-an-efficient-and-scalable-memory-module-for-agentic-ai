# Hardening Report (iteration 11)

## Summary

The old gym scored a 72-question templated synthetic set whose labels sat in `data/`. It also trusted self-reported operation counts and evidence text. Exhaustive lexical matching solved it (100%), and seed noise (rank range 2.17) was larger than the weaker-variant effect.

The rebuilt gym uses the paper's own benchmark, LoCoMo:
- 4 visible training conversations (581 questions).
- 6 held-out test conversations (955 questions) that exist only in `eval/test/`.

`scripts/evaluate_test.sh` runs every retriever in `scripts/retrievers/` on a label-free copy of the held-out conversations. The run happens in a sandboxed view of the workspace that has no `eval/` and no `.git`. The evaluator reads only the ranked entry IDs. Every scored number is recomputed from its own corpus and labels.

Results on the hidden test:
- Better results now score higher and worse results lower, by far more than seed noise.
- Every major shortcut from `REDTEAM.md` now ties or fails.
- One shortcut is left open: deliberately reading the evaluator's label file through an absolute path. It can't be closed inside a shared container.

All numbers below come from job `9aae9672-758` (`redteam/hardening/results/`, produced by `python redteam/hardening/run_hardening.py`).

**How rank delta is computed:** Σ |coefficient| × improvement over the reference, taken in its better direction, divided by the metric's standard deviation across the 21 runs of this audit (failed runs included at their failure values). Valid-runs-only normalisation gives the same ordering (`summary.json`).

**How CIs are computed:** paired bootstrap over questions, so every method is scored on the same resampled questions.

## What was fixed

| Requirement | Old gym | Now |
|---|---|---|
| Test labels hidden | Labels in `data/memory_qa.json`; the generator in `data/` regenerated them | Test labels only in `eval/test/locomo_test.json`, built only by `eval/test/prepare_test_split.py`. Synthetic data and generator deleted. |
| No-training method scored on unseen instances | Scored saved outputs on visible questions | The evaluator runs each retriever on held-out conversations, from a label-free input file in a private temp directory |
| Scored numbers recomputed | Evidence text, token count and `bit_operations` taken from the artifact | Only `retrieved_entry_ids` is read. Context text, answer-token recall and token footprint are rebuilt from the evaluator's corpus. Operation counts are not scored. |
| Comparison side fixed by `eval/` | Ground truth reloaded from a mutable `data/` file | Corpus, labels, budget (10 entries), failure floor (5% recall) and test size are fixed in `eval/test/`. Labels are loaded before any retriever runs. |
| Impossible values / failed constraints | Negative ops accepted; empty evidence outranked the reference | Malformed, over-budget, duplicate, unknown or cross-conversation output, or recall below 5%, is scored as failed: quality 0 and the maximum context the budget allows |
| Effect larger than seed noise | 36 questions; seed rank range 2.17 | 955 questions; seed rank range **0.083**; recall range 1.84 points |
| Brute force must not solve the test | Exhaustive lexical baseline 100% | Exhaustive BM25: **55.97%** recall@10 |
| Train/test comparable | n/a | Reference recall 23.80 (train) vs 24.42 (test); BM25 56.51 vs 55.97 |
| `evaluate_test.sh` with no args scores every method | Enumerated saved outputs | Enumerates `scripts/retrievers/*.sh`, the same interface as train, with no method name hardcoded |

## Better and weaker results (hidden test)

| Run | Recall@10 | Hit@1 | Answer-token recall | Worst category | Context tokens | Rank delta | Paired recall diff (95% CI) | Paired rank-delta CI |
|---|---:|---:|---:|---:|---:|---:|---|---|
| **reference `hippocampus` (seed 13)** | 24.42 | 9.32 | 39.60 | 12.71 | 491.1 | 0 | | |
| reference, seed 14 | 26.26 | 9.21 | 40.45 | 12.06 | 491.7 | +0.083 | +1.84 [−1.13, +4.80] | [−0.12, +0.28] |
| reference, seed 15 | 25.00 | 9.42 | 39.73 | 12.52 | 490.7 | +0.027 | +0.62 [−2.28, +3.39] | [−0.17, +0.22] |
| better: signature candidates re-ranked by BM25 | 36.95 | 28.06 | 45.35 | 20.08 | 401.9 | **+1.195** | +12.56 [+10.42, +14.72] | [+1.04, +1.36] |
| exhaustive BM25 baseline | 55.97 | 31.94 | 55.49 | 26.19 | 332.4 | +2.436 | +31.57 [+28.42, +34.64] | [+2.22, +2.65] |
| variant: frequency (IDF)-weighted keywords | 23.25 | 7.33 | 39.99 | 10.77 | 498.8 | −0.116 | −1.13 [−2.78, +0.46] | [−0.24, −0.02] |
| weaker: 16-bit signatures | 10.87 | 3.25 | 33.28 | 5.38 | 549.9 | **−0.981** | −13.56 [−16.37, −10.87] | [−1.18, −0.82] |
| weaker: previous iteration's configuration | 12.40 | 3.87 | 32.31 | 2.08 | 471.5 | −0.887 | −12.02 [−14.84, −9.07] | [−1.08, −0.68] |
| weaker: one-bit signatures | failed (2.68 raw) | | | | | **−2.454** | | |
| recency baseline | failed (1.05 raw) | | | | | −2.454 | | |

**Before → after:**
- Honest better variant: +3.17 (inside a 2.17 seed spread on 36 questions) → **+1.195**, CI [+1.04, +1.36], against a 0.083 seed range.
- One-bit ablation: −1.32 (smaller than the seed spread) → **failed**, −2.45.
- 16-bit ablation: −0.98, with a paired CI far from zero.

The IDF variant is not an improvement (−0.12), and it scores slightly lower, as it should.

## Shortcuts (hidden test)

| Shortcut (old name → re-run) | Before (old gym rank delta) | Fix | After |
|---|---:|---|---:|
| visible labels → `sc_train_label_lookup` (copies labels from `data/` by question) | +3.659 | Test questions and labels are not in `data/` | **failed** (−2.454) |
| generator answers | +3.659 | Generator deleted; the test split is built only in `eval/test/` | no route left (not runnable) |
| ID-only labels | +3.605 | Labels hidden; text rebuilt from IDs | no route left (same as above) |
| forged text, omitted / negative / null operations, row gold → `sc_forged_fields` (reference IDs plus forged text, `bit_operations=-1e12`, gold, answer, score fields) | +0.993 / +3e-10 / +0.046 / crash / 0 | Only `retrieved_entry_ids` is read | **tie** (0.000) |
| relabel dataset, replace corpus → `sc_relabel_visible_data` (rewrites `data/` labels and a corpus entry) | +4.393 / +4.505 | Evaluator uses its own corpus and labels in `eval/test/` | **tie** (0.000) |
| new: `sc_relabel_hidden_absolute` (follows the sandbox symlink and overwrites the evaluator's label file on disk) | — | Labels are loaded into memory before retrievers run | **tie** (0.000) |
| prewrite scores → `sc_prewrite_scores` | 0 | Evaluator writes `scores_test.json` last | **tie** (0.000) |
| empty output → `sc_empty_output` | −2.221 | Recall floor | **failed** |
| wrong IDs + answer text → `sc_single_wrong_id` | −1.322 | Text ignored; recall floor | **failed** |
| new: `sc_over_budget` (50 entries) | — | Budget check | **failed** |
| new: `sc_longest_entries` (10 longest turns, to collect answer words) | — | Context cost counted; evidence recall dominates | −1.497 |
| new: `sc_hidden_labels_relative` (opens `eval/test/...` from its working directory) | — | Sandbox has no `eval/` | **failed** |
| new: `sc_hidden_labels_absolute` (resolves the sandbox symlink to the real workspace and reads `eval/test/locomo_test.json`) | — | **Not closable here** | **+7.248 (still pays)** |
| baseline poisoning | 0 (tie) | Not replayed. Baselines are context only, and the reference is frozen in `scores_test.json`. | tie by construction |

### Shortcuts left open
1. **Reading the evaluator's private files at test time** (`sc_hidden_labels_absolute`; reading git objects is the same class).
   - The retriever runs as the same user, in the same container, as the evaluator. Any file the evaluator can read, a deliberately written retriever can read by absolute path.
   - The sandbox stops accidental and relative-path access only. Closing this fully needs OS-level isolation (a separate user or mount namespace), which this job environment does not provide.
   - The attack is explicit tampering with `eval/`, easy to spot with a search for `eval/test`, `realpath` or `.git` in method code. `scoring/CONSTRAINTS.md` forbids it.
2. **Embedding public LoCoMo labels.**
   - LoCoMo is public, so a submission could hard-code its answers or evidence IDs. This is the same class as above: external labelled data, forbidden in `CONSTRAINTS.md`.
   - It is inherent to using the paper's real benchmark, which was needed so that brute force no longer solves the test.
3. **Search cost is not scored.**
   - Latency and operation counts cannot be measured without timing or trusting the method, so they were removed from scoring.
   - A slow method is therefore not penalised. This is a limit on what the gym measures (headroom), not a loophole.

## Reference before → after

| | Old gym (synthetic, 36 test questions) | New gym (LoCoMo held-out, 955 questions) |
|---|---|---|
| Reference metrics | hit@1 33.33, hit@3 55.56, F1 2.37, tokens 62.6, ops 7,468.5 (self-reported) | recall@10 **24.42**, hit@1 9.32, answer-token recall 39.60, worst category 12.71, context tokens 491.1 |
| Seed spread | rank 2.17 (hit@1 38.9 points) | rank 0.083 (recall 1.84 points) |

### Changes to the reference implementation
These are setup and fidelity fixes. They do not change the paper's algorithm:
- **Memories and I/O:** one memory (two DWMs) per conversation, and the new I/O contract.
- **Faster bit levels:** bytearray bit-levels with `count`-based rank during append, and no duplicate rebuild. The DWM self-test still passes.
- **Dense hyperplanes:** random hyperplanes are now dense Gaussian, as in the paper's Appendix G. The old 16-non-zero hyperplanes projected a lone keyword to about 0, giving near-constant all-ones signatures.
- **Ranking:** candidates are ranked by how many query keywords co-occur in the entry span, which is the paper's "all (or many) of these query signatures co-occur". The old version summed per-position matches.
- **Parameters:** radius 8, window ±1, keyword-alone queries. These are absent from the paper and were chosen on the training conversations only. Train recall@10: old configuration 12.6, chosen 23.8; radius 7 gives 18.4, radius 9 gives 15.9.
- **Unchanged from the paper:** D = 512 and d = 32.
- **Reconstruction:** returned entries are still reconstructed losslessly from the Content DWM; the evaluator ignores that text.

### Does the reproduction show the paper's claim?
- **Against lightweight memory:** the reference recovers 24.4% of evidence, against 1.05% for the most-recent-entries baseline. That is the paper's direction versus MemoryBank-style memory.
- **Token footprint:** it delivers 491 tokens per question, against about 20.7K for the full history (42× less). That matches the direction of the paper's 14× token claim.
- **Against exhaustive BM25:** stated plainly, exhaustive BM25 over raw text recovers more than twice as much evidence (55.97%) with fewer tokens. The paper never compared against BM25. On LoCoMo turn-level evidence, the 32-bit context signatures lose much of the lexical signal, which is where the method falls short and where the headroom lies.

## Headroom check
- **No scored reference metric is at its bound:** recall 24.4, hit@1 9.3, answer-token recall 39.6 and worst category 12.7 are all far below 100, and context tokens (491) are far above the minimum.
- **Better variants exist:** BM25 re-ranking of the method's own candidates (+1.195) and exhaustive BM25 (+2.436) both score above the reference, beyond paired noise.
- **Nothing is trivially at the bound:** exhaustive BM25 reaches only 56% recall.
- **What was added:** the whole scored experiment moved to where the paper's method falls short, real long-conversation evidence retrieval on LoCoMo, and the reference and baselines were run on it.
- **Simple baseline:** recency is clearly below the reference. It is recorded as failed, with raw numbers kept under `_status`.

## Weights
Single experiment (weight 1.0). Coefficients:
- `evidence_recall_at_10` **1.0**: primary; the paper's accuracy axis maps to recovering the evidence.
- `evidence_hit_at_1` 0.4 and `answer_token_recall` 0.4: ranking quality, and whether the answer reaches the context.
- `worst_category_recall` 0.3: the paper reports all four LoCoMo groups.
- `avg_context_tokens` −0.2: the paper's token-footprint claim; the only efficiency quantity measurable here.

Latency and operation counts were the old cost metrics. They were removed because they could not be measured without trusting the method.

## Could not fix
- In-container isolation of the evaluator's files from a deliberately malicious retriever (see "Shortcuts left open").
- The paper's LLM-answer metrics (F1, BLEU-1, LLM judge) and latency are not reproduced. They need an LLM and timing. They are kept unchanged in `scoring/reference.json` under `_paper_reported`.
- The old audit harness (`redteam/audit.py` and the case folders) targets the deleted synthetic gym. It is kept as a historical record and is not runnable against the new gym; `redteam/hardening/` replaces it.
