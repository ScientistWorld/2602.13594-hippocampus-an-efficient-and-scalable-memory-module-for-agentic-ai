# Scientist Constraints

## Interface
Submit methods as retriever scripts in `scripts/retrievers/<name>.sh` with the contract in `briefing/evaluation.md`. The hidden evaluator runs every script there on conversations you cannot see, so the method must work on new conversations without manual steps and without internet.

## Data
Use only the memory input the evaluator passes to your script. Do not read evaluator files (`eval/`), git history, or copies of the LoCoMo questions, answers or evidence labels from any other source. LoCoMo is public, and embedding its labels is a shortcut, not a method. Training or tuning may use `data/locomo_train.json`, including its labels.

## Output budget
At most 10 entries per question, all from that question's conversation, with no duplicates. Only the ranked entry IDs are scored; the evaluator rebuilds the delivered text itself.

## Resources
No paid APIs, external LLM calls, or downloads at test time. Do not add large pretrained neural retrievers whose gains come from model scale; the paper's contribution is a lightweight memory substrate.

## Compliance Checklist
- [ ] Method runs from `scripts/retrievers/<name>.sh` on the label-free input
- [ ] At most 10 entries per question, from the question's own conversation
- [ ] No access to `eval/`, git history, or external label copies
- [ ] No paid or external API calls during retrieval
