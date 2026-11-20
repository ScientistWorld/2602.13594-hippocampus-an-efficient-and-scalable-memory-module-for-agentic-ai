"""Per-question lexical overlap with the evidence, for the style-calibration pass.

    python3 -I eval/test/authoring/tools/overlap_report.py conv-30 <questions.json>

Prints, for each question index: category, overlap (fraction of the question's
content words, speaker names excluded, that occur in its evidence turns), and
the overlapping words; then per-category means next to the public LoCoMo
train-split means the set should match.
"""
import json, sys
from collections import defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from overlap_stats_lib import overlap_words, TRAIN_MEANS  # noqa

conv, path = sys.argv[1], Path(sys.argv[2])
dump = (HERE / "dumps" / f"{conv}.txt").read_text().splitlines()
text = {}
for line in dump:
    if line.startswith("[conv-"):
        eid = line[1:line.index("]")]
        text[eid] = line[line.index("]") + 1:].replace("(PUBLIC-EVIDENCE)", "")
names = {w.lower() for w in dump[0].split("speakers:")[1].replace(" and ", " ").split()}
data = json.loads(path.read_text())
by = defaultdict(list)
for i, q in enumerate(data["questions"]):
    frac, words = overlap_words(q["question"], [text[e] for e in q["evidence_entry_ids"]], names)
    by[q["category"]].append(frac); by["ALL"].append(frac)
    print(f"{i:3d} {q['category']:<12} overlap={frac:.2f} shared={sorted(words)}")
print("category means (this set -> train target):",
      {k: f"{sum(v)/len(v):.2f}->{TRAIN_MEANS.get(k, float('nan')):.2f}" for k, v in sorted(by.items())})
