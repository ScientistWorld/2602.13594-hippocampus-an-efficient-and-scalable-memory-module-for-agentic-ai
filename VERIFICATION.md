# Verification Report

## Initial Assessment

The workspace started at `core_claim_plus` with a real HIPPOCAMPUS-style implementation: token content stream, binary signature stream, Dynamic Wavelet Matrix primitives, Hamming retrieval, span validation, and exact reconstruction. The latest CPU test job completed successfully, and `python validate.py --compare` passed locally.

The claimed milestone is justified for a portable core-claim reproduction: the paper's memory-substrate mechanics run end to end, produce reusable artifacts, and are scored against quality and efficiency constraints.

## Issues Found

- Minor: `scoring/TARGETS.md` did not list every supporting metric currently scored in `scores.json`.
- Minor: `scoring/reference.json` used paper-reported LoCoMo values as contextual references for gym retrieval metrics that the paper did not directly report, but did not explain the mapping.
- Minor: `PROGRESS.md` overstated the synthetic benchmark difficulty. A lexical sanity baseline is near-perfect because generated questions share surface entities with answer-bearing entries.
- Residual limitation: the benchmark is synthetic and easier than LoCoMo/LongMemEval. It is useful for validating the compressed memory substrate, but less suitable as a broad open-ended retrieval benchmark.

## Fixes Applied

- Updated `scoring/TARGETS.md` to include `gold_entry_recall` and `worst_category_hit_at_1`.
- Added a `notes` field to `scoring/reference.json` explaining the paper-to-gym metric mapping and the replacement of wall-clock latency with bit-operation count.
- Corrected `PROGRESS.md` to explicitly document that lexical matching is a strong sanity baseline on this synthetic data.
- Added a final verification entry to `MILESTONES.md`.

## Final Judgment

The workspace is ready to serve as a research gym for the reproduced core claim. Improve-mode agents can inspect and extend the HIPPOCAMPUS implementation; from-scratch agents can use the method-agnostic data/eval path without importing `method/`. The main caveat is evaluation difficulty: the bundled benchmark is portable and API-free but does not match the semantic and generation difficulty of the original LoCoMo/LongMemEval experiments.

- Milestone: core_claim_plus
- Ready for gym use: yes
- Confidence: medium
- Key limitation: synthetic retrieval data is easier than the paper's full benchmarks and is vulnerable to lexical matching.
