> **Superseded (iteration 11):** this file describes the earlier synthetic-benchmark gym. The current gym (LoCoMo, evaluator-run retrievers) is described in `HARDENING.md`, `briefing/` and `scoring/`.

# Train/Test Evaluation Design Notes

## What I Checked

- Compared `scripts/evaluate_train.sh` and `scripts/evaluate_test.sh`; both enumerate `outputs/*/retrieval_results.jsonl`, call their own split evaluator, and write `scoring/scores_train.json` / `scoring/scores_test.json` respectively.
- Checked for hardcoded method defaults in the train/test scripts; both discover artifacts from disk when no paths are provided.
- Checked for cross-import leakage between `eval/train/` and `eval/test/`; neither split imports from the other.
- Checked `scoring/reference.json` for paper-agreement metrics; none of the scored metrics are reproduction-error or published-value matching metrics.
- Confirmed `scoring/scores_train.json` and `scoring/scores_test.json` are absent.
- Ran `bash -n` on both train/test wrapper scripts.

## What Changed

- Replaced the visible seed-derived train split with an explicit balanced train ID list. This removes the train-side seed/procedure leak that made the held-out complement easy to infer.
- Replaced the test split with its own explicit balanced ID list, preserving 36 train and 36 test questions with 12 questions per category in each slice.
- Added evaluator validation for the retrieval contract: maximum three retrieved entries, no duplicate retrieved entry IDs, known entry IDs only, and no cross-conversation retrieval.
- Added method-agnostic anti-shortcut metrics to both train and test:
  - `gold_entry_recall` catches methods that retrieve only one supporting item on multi-hop questions.
  - `worst_category_hit_at_1` catches methods that overfit one question category.
  - `reconstruction_exact_match` catches answer-stuffing or generated evidence that does not match the retrieved memory entry.
  - `avg_retrieved_entries` penalizes always filling the top-three budget when fewer entries suffice.
- Updated `scoring/reference.json` so every scored metric has `higher_is_better`, `coefficient`, and `description`.

## Runtime Concerns For Next Iteration

- I did not run the evaluators or produce scores in this design-only pass. The runner should verify that existing artifacts still pass the stricter retrieval validation.
- `reconstruction_exact_match` uses token-normalized equality against the canonical memory entry text. This should work for the current artifact schema, but a future method that returns faithful text with different tokenization may score lower on this constraint.
- The dataset remains small: 36 questions per slice. The added category and reconstruction metrics reduce shortcut risk, but score variance can still be noticeable.
- The full `data/memory_qa.json` still contains all questions and labels. The split no longer leaks a complement-generating seed through train code, but true secrecy depends on the benchmark runner withholding `eval/test/` from future agents as intended.
