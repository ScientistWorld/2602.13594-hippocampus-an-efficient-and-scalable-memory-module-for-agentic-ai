# Final hardening report

Job 370ea91b-ced completed successfully on 2026-11-20. Measured better and weaker variants rank in the right direction, beyond seed noise. The evaluator rejects the tested file-reading and malformed-output attacks and recomputes all scores from entry IDs.

**The gym still does not meet every requested scientific criterion.** Exhaustive BM25 substantially outranks the reference; public-label priors also still outrank it. The reference omits the paper's LLM keyword extraction, and the scored quantities are retrieval proxies rather than the paper's end-to-end answer metrics. These are unresolved failures, not successful headroom checks. The earlier core_claim_plus milestone is withdrawn under the reproduction-integrity rule; the current milestone is **none**.

## Review follow-up and final setup

REVIEW.md identified that downloading public LoCoMo supplied the old held-out answers. The final hidden test instead uses **659 newly authored, evidence-checked questions** on six held-out conversations: single-hop 307, temporal 163, multi-hop 131, open-domain 58. Questions, answers, evidence IDs, support notes, assembly code and the merged corpus live only in eval/test/. The 581 public questions on four other conversations remain the visible training split. All methods receive the same label-free histories and questions at evaluation time.

The private questions include both publicly cited and previously uncited evidence turns. A public evidence list therefore does not identify the private answers exactly. The private set was already present at the start of this final audit. Fixed its assembly script to read the complete verified/ and supplement/ sources instead of incomplete calibration drafts, and verified exact reconstruction of the released questions. No released question or label changed.

The previous report's 955-question public test is superseded. Its historical measurements below are identified separately. No private answer or question-level scoring record was moved into the visible workspace.

## Changes in this iteration

- **Required isolation:** removed the readable-file fallback. Methods run in user, mount and PID namespaces with locked empty mounts over eval/ and .git. Relative paths, resolved workspace paths, /proc roots and unmount attempts were tested. If isolation fails, no method runs and every method gets all five failure values. The container explicitly installs the required mount/namespace tools.
- **Complete failure accounting:** missing output, invalid UTF-8, malformed/deep JSON, oversized output, duplicate/missing questions, invalid IDs and budget violations fail the whole run. Every quality metric becomes zero and context cost becomes the largest possible under the ten-entry budget. Below-5% recall receives the same vector. Raw diagnostics outside results cannot earn rank.
- **Independent measurements:** only ranked entry IDs are accepted. Context and every metric are rebuilt from the evaluator's loaded corpus and labels. Submitted text, gold, scores, flags, operation counts and verdicts have no authority.
- **Fixed comparisons:** independent frozen BM25 and recency implementations live inside each split's evaluator. Neither imports editable baseline or method code. Comparison diagnostics and full-history cost are computed before methods run. Poisoning visible baseline code left them unchanged.
- **Reproducible runs:** deterministic summation, PYTHONHASHSEED=0 and fixed reference seed 13. Official reference and baselines ran sequentially, with no other audit retriever alongside them. Variants also ran sequentially. Removed the isolation probe's wall-clock timeout. The method path has a four-CPU-hour process limit and no wall-clock cutoff.
- **Evidence and packaging:** raw official/variant outputs and paired records stay under eval/test/audit/, behind isolation. Every reference metric was refreshed from the official run, replacing the stale single-metric entry. Official score files contain only registered reference/baseline runs. The default scripts/run.sh again reproduces the reference end to end; the full audit remains separately runnable.

The contract preflight exercised both independent evaluators, including forced isolation denial, and checked private evidence IDs/support records. The job ran the DWM self-test and python validate.py --compare; all passed. Initial "isolation: denied" stderr lines are the intentional fail-closed preflight, followed by successful isolation for real runs.

## Reference before and after

| Setting | Recall@10 | Hit@1 | Answer-token recall | Worst category | Context tokens |
|---|---:|---:|---:|---:|---:|
| Previous report: 955 public held-out questions | 24.42 | 9.32 | 39.60 | 12.71 | 491.1 |
| Private set on disk before final fixes | 26.39 | 9.10 | 46.25 | 10.49 | 507.8 |
| Final official rerun: 659 private questions | **26.39** | **9.10** | **46.25** | **10.49** | **507.8** |

The private reference vector is exactly unchanged by final hardening. Public-to-private differences measure changed questions, not an improved method. The official test vector exactly matches the audit's independently run reference in its copied workspace.

Train reference recall is 23.80 versus test 26.39. BM25 is 56.51 versus 69.05, so private questions are easier for lexical retrieval; comparable difficulty is imperfect. Train/test context costs are 493.1/507.8 for the reference and 347.2/349.1 for BM25. Raw recency recall is 0.90/1.13; both fail the utility floor.

## Do better results score higher?

Yes for measured variants. The final audit contains **34 attempts**, including 16 complete failures. Its diagnostic rank delta adds experiment weight times each metric's absolute coefficient times directed improvement over the reference divided by population standard deviation across those attempts. Direction comes only from higher_is_better; a constant metric contributes zero. Valid-only normalization preserves the main better/reference/weaker ordering.

Only experiment results in scoring/scores_test.json (or scores_train.json for train) are ranked by the gym. These audit deltas are diagnostic. Different future populations change normalization and tradeoffs.

The "before" column uses the 29-attempt private audit present before the final patches (commit e4e2191, redteam/hardening/results/summary.json). Raw metrics are identical; adding parser-failure controls changed normalization, not outcomes. All variants were rerun from final code.

| Method | Recall before → after | Rank delta before → after | Final paired recall difference, 95% CI | Final paired rank-delta CI |
|---|---:|---:|---|---|
| Reference | 26.39 → 26.39 | 0 → 0 | — | — |
| Candidate reranking with BM25 | 38.34 → 38.34 | +1.712 → **+1.783** | +11.95 [9.72, 14.42] | [1.49, 2.04] |
| BM25 with adjacent-turn context and stemming | 74.72 → 74.72 | +4.912 → **+5.097** | +48.33 [44.58, 52.19] | [4.68, 5.42] |
| Exhaustive BM25 baseline | 69.05 → 69.05 | +4.220 → **+4.378** | +42.67 [39.05, 46.57] | [3.98, 4.70] |
| IDF weighting variant | 22.38 → 22.38 | −0.250 → **−0.257** | −4.00 [−6.27, −1.71] | [−0.47, −0.06] |
| Weaker, 16-bit signatures | 10.96 → 10.96 | −1.199 → **−1.237** | −15.43 [−18.42, −12.20] | [−1.52, −0.95] |
| Previous configuration | 13.38 → 13.38 | −0.943 → **−0.975** | −13.00 [−16.45, −9.20] | [−1.30, −0.66] |
| Weaker, one-bit signatures | failed → failed | −2.771 → **−2.832** | raw recall 2.45 | — |

Intervals use 1,000 paired bootstrap question resamples, seed 0, with the same resampled inputs for each method and reference. Table point differences are full-test means; the summary also records bootstrap means. These intervals describe question sampling on six fixed conversations, not uncertainty across new conversations.

Reference seeds 13/14/15 give recalls 26.39/26.23/27.81: **1.58-point range**, versus the reranker's 11.95-point gain and the 16-bit variant's 15.43-point loss. Their rank range is **0.086**, versus +1.783 and −1.237. Fixing the seed removes this variation from stored reference scores. In REDTEAM.md's original synthetic audit the honest gain was +3.173, one-bit loss −1.317 and seed range 2.173; that weak-effect/noise problem is resolved on this larger test.

## Major shortcuts: fixes and retests

Historical "before" deltas come from REDTEAM.md's synthetic test unless identified otherwise. Their scales/cohorts differ from this audit. Every final failure has quality vector (0,0,0,0) and context cost **784.9878603945372**, producing delta **−2.832** in this cohort.

| Shortcut | Before | Defense / final result |
|---|---|---|
| Copy visible test labels | +3.659 | Private labels under eval/test/; train-label lookup finds no test evidence and **fails, −2.832**. |
| Rebuild synthetic generator answers | +3.659 | Old generator/synthetic test removed in earlier hardening. Private assembly stays only in eval/test/. No old-generator replay is applicable. |
| Label IDs with empty evidence | +3.605 | No visible private labels. For legitimate IDs, context and cost are rebuilt; empty/forged text cannot erase cost. |
| Read evaluator labels by relative/absolute path | Absolute read +7.248 in previous 955-question report; private pre-patch audit already failed when namespaces worked | Required isolation also closes fallback. Both paths **fail, −2.832**, in copied and real workspaces. |
| Escape through /proc or unmount eval/ | Not in original audit | Locked mounts/PID isolation: **fails, −2.832** in real workspace. Forced isolation denial also fails without launching a method. |
| Forge text / row gold / scores / omit, negate or null operations | +0.993 / 0 / tiny positive / +0.046 / evaluator crash | Fields ignored. Combined fixture executes real reference retrieval and **ties, 0** on every metric. Wrong IDs plus forged answer fail. |
| Relabel visible data / replace corpus | +4.393 / +4.505 | Evaluator owns loaded corpus. Fixture executes real reference and **ties, 0**. Visible train file was changed in the attack copy; private labels were not. |
| Overwrite hidden labels on disk | Tie in previous report | Hidden/read-only eval mount; private file unchanged. Fixture runs genuine reference and **ties, 0**. |
| Poison visible baselines | Tie | Comparison procedures owned by eval/; assertion confirms them unchanged. Genuine reference retrieval **ties, 0**. |
| Prewrite perfect score files | Tie | Evaluator writes scores last; fixture runs real reference and **ties, 0**. |
| Empty retrieval / wrong IDs plus forged answer | −2.221 / −1.322 | Utility floor/rebuilt context: **both fail, −2.832**. |
| Return 50 entries | Not in original audit | Ten-entry constraint: **fails, −2.832**. |
| Invalid UTF-8 / malformed JSON / missing file / duplicate question | Previously risked evaluator abort or absent result | All four new attacks **fail, −2.832**, with every metric present. |
| Ten longest turns to harvest answer words | −1.497 on previous public test | Rebuilt cost/evidence scoring: recall **5.17**, 775.1 tokens, delta **−1.833**. |
| Public LoCoMo question/evidence lookup | Revealed old public answers | Fixture fails on a nonexistent public evidence ID, **−2.832**. This alone does **not** prove resistance to corrected public-label lookup. See open shortcuts. |

A tie is not counted as closing a major shortcut merely because it fails to beat the reference. Each tied fixture performs full genuine reference retrieval; the attempted extra mutation changes no metric. It shows no shortcut to producing those predictions. A new cheap procedure producing reference-quality predictions would need separate assessment.

## Shortcuts and scientific weaknesses left open

1. **Embedded public held-out label priors remain profitable.** Private questions remove the exact public answer key, but conversation histories are public. Boosting publicly cited evidence plus BM25 gives **51.39 recall, +2.220** (before +2.148). Avoiding those turns plus BM25 gives **55.73, +3.181** (before +3.066). Avoiding them with reference candidates gives **24.44, −0.047**. These priors are forbidden, but raw-output validation cannot identify an embedded prior. They are left to the separate code grader. Both BM25 attacks lose to honest BM25 (69.05) and the context variant (74.72), yet outrank the reference, so this remains an **unclosed major shortcut**. The failed exact-lookup fixture does not establish otherwise.
2. **Exhaustive lexical search remains a baseline-calibration failure.** It does not saturate, but recovers 69.05% of evidence with 349.1 tokens, versus reference 26.39% and 507.8. It is an honest alternative, not a loophole. The test was not scaled until exhaustive search ceased to pay. Calling this valid headroom would contradict the requested criterion. No larger-history experiment was completed.
3. **Search cost is not measured.** Appendix F also scans signatures linearly; this is not exponential objective search. A self-reported budget cannot bind private lexical computation. CPU limits are resource guards, not scientific speed measurements. Slower honest procedures remain expressible; methods are not restricted to reference settings.
4. **Paper fidelity and scientific quantity are incomplete.** The identifiable dual-DWM, random-indexing, Hamming search, metadata validation and exact reconstruction steps are present. The implementation uses Appendix G's Gaussian-hyperplane hashing rather than Section 3.3's top-activated coordinates, and substitutes stopword filtering for LLM keyword extraction. The missing step was not restored. Word-token context and evidence/answer-token coverage are retrieval measurements, not the paper's LLM answer F1, BLEU-1, judge score or billed LLM tokens. LongMemEval and the paper's neural/memory baselines were not reproduced. No full joint claim is established; the previous milestone overclaimed.

## Headroom and weights

No scored reference metric is at its bound: quality is far below 100%, and 507.8 context tokens exceeds the minimum. Neither BM25 nor the 74.72% context variant reaches the bound. The latter is 5.67 recall points above BM25 on the same inputs; the method-specific reranker also clearly beats the reference. There is measured room for improvement, but **the baseline-calibrated headroom check still fails**. No new scored experiment was added; the private questions replace exposed public questions in the existing experiment. Weakest-category recall supplies scored pressure on open-domain and multi-hop weaknesses.

Weights are unchanged: experiment 1; coefficient magnitudes recall 1.0, hit@1 0.4, answer coverage 0.4, weakest category 0.3, context 0.2. Lower context direction comes from higher_is_better=false, not coefficient sign. Complete failure vectors are componentwise no better than any valid run, so a failed task cannot win through cheap context or missing metrics.

The reference delivers about **40 times less context** than full history (507.8 versus 20,461.9 words) and beats recency on evidence recall (26.39 versus 1.13 raw). These match the paper's directions on limited comparisons, but do not establish its joint claim against competitive baselines. All paper-reported results remain unchanged under _paper_reported in scoring/reference.json and are not targets on the proxy scale.

## Reproduction and verification

- bash scripts/run.sh: public-artifact setup, contract preflight when available, DWM self-test, sequential train/test reference and baselines, validation. No package installation in the run path.
- python redteam/hardening/run_hardening.py: optional full sequential audit after reproduction. Audit outputs are separate; official score files remain reference/baseline only.
- Official results: scoring/scores_test.json, scores_train.json; scores.json is the train copy. All five reproduced reference metrics are frozen in reference.json.
- Audit evidence: redteam/hardening/results/summary.json, summary.md, split/variant aggregate JSON, side-effect assertions. Regenerable logs are ignored. Raw outputs and paired records remain only in eval/test/audit/.
- The completed job reran final-code reference/baselines, better/weaker/seeds and fixed attacks, froze scores, and passed validate.py --compare.

Evaluator/private-label defenses are packaged and verified. Unresolved calibration, profitable public-label priors and fidelity omissions prevent claiming that all hardening/reproduction requirements are met.
