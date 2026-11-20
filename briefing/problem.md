# Problem

Agentic AI systems need persistent contextual memory: past dialogue turns must be stored outside the LLM context window and the few that matter must be recalled when a later question arrives.

The task is long-conversation memory retrieval on LoCoMo (Maharana et al., 2024). Each LoCoMo conversation is one agent's memory: 19-32 sessions between two people, roughly 370-690 dialogue turns (about 20K word tokens). Every dialogue turn is one memory entry with an ID, session number, turn number, session timestamp, speaker and text. Given a question about one conversation, a memory system returns a ranked list of at most 10 entries from that conversation. The returned entries form the context an LLM would answer from.

Questions come from four LoCoMo groups: single-hop, multi-hop (the answer needs several turns), temporal, and open-domain (the answer must be inferred from what was said). Each question is labelled with the turn(s) that contain its evidence.

A good memory system recovers the evidence turns while delivering little context per question. Returning the whole history (about 20K tokens per question) or the most recent turns are the two trivial extremes.

Data:
- `data/locomo_train.json` holds 4 visible conversations with 581 labelled questions (built by `scripts/download.sh` from the public release, pinned commit and checksum).
- The hidden test uses 6 other LoCoMo conversations that are not in the workspace, with a private set of 659 questions written for them in LoCoMo's style and four groups. These are not the public LoCoMo questions, and the public LoCoMo labels do not answer them. Your retriever is run on them at test time.
