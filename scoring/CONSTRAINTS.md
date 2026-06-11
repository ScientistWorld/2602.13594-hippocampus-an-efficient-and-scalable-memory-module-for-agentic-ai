# Scientist Constraints

## Data
Use `data/memory_qa.json` exactly as provided for scoring. Do not add external conversations, extra labels, or generated paraphrases to the scoring set.

## Output Budget
Return at most three memory entries per question. The benchmark is about selective recall, so returning larger contexts changes the problem.

## Evaluation
Use `scripts/evaluate.sh` and the artifact schema already used by `outputs/*/retrieval_results.jsonl`. Do not modify gold labels, metric definitions, or the scoring split.

## Resources
Do not use paid APIs or external LLM calls during scoring. The paper's contribution is a memory substrate, and API-based answer generation would confound retrieval with model capability.

## Compliance Checklist
- [ ] Scoring uses only `data/memory_qa.json`
- [ ] Each question has at most three retrieved entries
- [ ] `scripts/evaluate.sh` is unchanged for final scoring
- [ ] No paid or external API calls are used during scoring
