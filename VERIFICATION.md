> **Superseded (iteration 11):** this file describes the earlier synthetic-benchmark gym. The current gym (LoCoMo, evaluator-run retrievers) is described in `HARDENING.md`, `briefing/` and `scoring/`.

# Verification Report

## Initial Assessment

The workspace started at milestone `core_claim_plus`. The claimed method implementation is recognizable as the paper's memory substrate: it builds separate compressed streams for stored content and retrieval keys, performs bounded candidate retrieval, validates spans, and reconstructs returned entries from the stored representation. The main evaluator reads JSONL artifacts and does not import from `method/`.

`python validate.py --compare` passed at the start of verification, and prior CPU-node jobs had completed the packaged workflow successfully.

## Issues Found

- Critical, fixed: `eval/train/evaluate_retrieval.py` and `eval/test/evaluate_retrieval.py` filtered artifacts to method names already present in `scoring/reference.json`. That would silently ignore a future scientist's new method name in train/test scoring.
- Minor, fixed: `scripts/run.sh` called train/test evaluators without explicit artifact paths, so stale ignored files under `outputs/` could affect split scores in a dirty workspace.
- Minor, fixed: `scoring/DIRECTION.md` described the paper's exact mechanism too specifically for a high-level method-safe guidance file.
- Cosmetic, fixed: a generated root-level `__pycache__/` directory was present and was removed.
- Residual limitation: the benchmark is synthetic and easier than LoCoMo/LongMemEval. A lexical sanity baseline can solve the current templated data very well, so the gym is best viewed as a portable core-claim environment rather than a full semantic-memory benchmark.

## Fixes Applied

- Removed the `reference.json` method-name filter from the train/test evaluators. They now score arbitrary artifact method names while still enforcing split membership, top-3 output size, known entries, duplicate checks, and conversation boundaries.
- Updated `scripts/run.sh` to refresh committed train/test scores from the official `hippocampus` and `recency_baseline` artifacts explicitly.
- Reworded `scoring/DIRECTION.md` to describe the allowed research family without naming the paper's specific internal mechanism.
- Reran `bash scripts/run.sh`; it completed successfully and `python validate.py --compare` passed.

## Final Judgment

The workspace is ready for core-claim gym use. Improve-mode agents can inspect and modify the reproduced method; from-scratch agents can use `data/`, `eval/`, and the shell evaluators without importing `method/`. The scoring includes both retrieval benefit metrics and efficiency constraints, with wall-clock time excluded from scored metrics.

The main caveat is difficulty: the bundled benchmark is small, synthetic, and vulnerable to lexical matching. This does not invalidate the implemented paper method, but it limits how much scientific weight to place on improvements beyond the documented core retrieval-efficiency claim.

- Milestone: core_claim_plus
- Ready for gym use: partial
- Confidence: medium
- Key limitation: synthetic retrieval data is easier than the paper's full LoCoMo/LongMemEval setup and is vulnerable to lexical matching.
