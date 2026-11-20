#!/usr/bin/env python3
"""Train-split evaluator for long-conversation memory retrieval.

Runs every registered retriever (scripts/retrievers/*.sh, or explicit scripts)
on the visible LoCoMo training conversations in data/locomo_train.json, then
scores the returned entry IDs against their evidence labels. It mirrors the
hidden-test protocol exactly (same input format, budget, metrics and failure
rules), so train scores are a faithful development signal.

Integrity rules enforced here:
* Retrievers receive a label-free copy of the memories and questions in a
  private temporary directory, and run from a sandbox view of the workspace
  that does not contain eval/ or .git, inside user/mount/PID namespaces where
  eval/ and .git are hidden (same run conditions as the hidden test).
* Retrievers are limited in CPU time, never in wall-clock time.
* Only the ranked entry IDs a retriever returns are read. Every scored number
  (evidence recall, answer-token recall, context tokens, ...) is recomputed
  from the evaluator's own copy of the corpus and labels; any other field a
  retriever writes is ignored.
* A run that breaks the output contract (missing/duplicate questions, unknown
  or cross-conversation entries, more than MAX_RETRIEVED entries) or that does
  not reach MIN_EVIDENCE_RECALL is scored as failed: every quality metric is 0
  and the context cost is set to the largest value the budget allows.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import resource
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path


SLICE = "train"
EXPERIMENT = "locomo_memory_retrieval"
ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "locomo_train.json"
MAX_RETRIEVED = 10
# Utility floor: below this evidence recall@10 the run has not solved the task
# (returning random entries gives ~1.7%; the most-recent-entries baseline ~0.4%).
MIN_EVIDENCE_RECALL = 5.0
# CPU-time limit per retriever process (not wall-clock, so results never depend
# on machine load). The reference retriever uses a few CPU-minutes.
RETRIEVER_CPU_LIMIT_S = 4 * 3600
# Retrievers run in their own user, mount and PID namespaces: eval/ and .git are
# covered by empty read-only mounts, the mounts are locked by a second nested
# user namespace (they cannot be unmounted from inside), and the evaluator's
# processes are invisible. If the host does not allow unprivileged namespaces, evaluation fails
# closed: no retriever runs with readable test labels.
ISOLATION_INNER = r"""
set -e
root="$1"; shift
for hidden in "$root/eval" "$root/.git"; do
  if [ -d "$hidden" ]; then mount -t tmpfs -o ro,size=4k,mode=0555 hidden "$hidden";
  elif [ -e "$hidden" ]; then mount --bind /dev/null "$hidden"; fi
done
exec unshare --user --map-root-user --mount -- "$@"
"""
CATEGORIES = ("multi_hop", "open_domain", "single_hop", "temporal")
SCORED_METRICS = (
    "evidence_recall_at_10",
    "evidence_hit_at_1",
    "answer_token_recall",
    "worst_category_recall",
    "avg_context_tokens",
)
TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")
ANSWER_STOPWORDS = frozenset(
    "a an the of in on at to for and or with by from is was are were be been it its that this as".split()
)


class RunFailure(Exception):
    pass


def tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def render(entry: dict) -> str:
    """Context delivered for one memory entry: its timestamp and full text."""
    return f"[{entry['date_time']}] {entry['text']}"


def load_dataset(path: Path) -> dict:
    data = json.loads(path.read_text())
    entries: dict[str, dict] = {}
    for conversation in data["conversations"]:
        for entry in conversation["entries"]:
            entries[entry["entry_id"]] = {**entry, "conversation_id": conversation["conversation_id"]}
    data["_entries"] = entries
    data["_questions"] = {q["question_id"]: q for q in data["questions"]}
    return data


def public_input(data: dict) -> dict:
    conversations = []
    for conversation in data["conversations"]:
        conversations.append(
            {
                "conversation_id": conversation["conversation_id"],
                "speakers": conversation.get("speakers", []),
                "entries": [
                    {key: entry[key] for key in ("entry_id", "session", "turn", "date_time", "speaker", "text")}
                    for entry in conversation["entries"]
                ],
            }
        )
    questions = [
        {key: q[key] for key in ("question_id", "conversation_id", "question")} for q in data["questions"]
    ]
    return {"split": SLICE, "conversations": conversations, "questions": questions}


def build_sandbox(base: Path) -> Path:
    sandbox = base / "workspace"
    sandbox.mkdir()
    for child in ROOT.iterdir():
        if child.name in {"eval", ".git"}:
            continue
        os.symlink(child, sandbox / child.name)
    # Retriever scripts call `python`; point it at this interpreter.
    bin_dir = base / "bin"
    bin_dir.mkdir()
    for name in ("python", "python3"):
        os.symlink(sys.executable, bin_dir / name)
    return sandbox


def isolation_prefix() -> list[str]:
    return [
        "unshare", "--user", "--map-root-user", "--mount", "--pid", "--fork", "--mount-proc", "--",
        "bash", "-c", ISOLATION_INNER, "isolate", str(ROOT),
    ]


def probe_isolation() -> tuple[bool, str]:
    """True if a namespaced child sees an empty eval/ (and .git) under ROOT."""
    if shutil.which("unshare") is None:
        return False, "unshare not available"
    check = 'test -d "$1/eval" && test -z "$(ls -A "$1/eval")" && ! test -e "$1/.git/HEAD"'
    try:
        proc = subprocess.run(
            isolation_prefix() + ["bash", "-c", check, "probe", str(ROOT)],
            capture_output=True,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"probe failed: {exc}"
    if proc.returncode != 0:
        return False, f"probe exit {proc.returncode}: {proc.stderr.decode(errors='replace')[-300:]}"
    return True, "user+mount+pid namespaces; eval/ and .git hidden"


def _limit_cpu() -> None:
    resource.setrlimit(resource.RLIMIT_CPU, (RETRIEVER_CPU_LIMIT_S, RETRIEVER_CPU_LIMIT_S))


def run_retriever(
    script: Path, input_path: Path, output_path: Path, sandbox: Path, log_path: Path, isolate: bool
) -> None:
    script = script.resolve()
    try:
        launch = sandbox / script.relative_to(ROOT)
    except ValueError:
        launch = script
    with log_path.open("w") as log:
        env = dict(os.environ)
        env["PYTHONHASHSEED"] = "0"
        env["PATH"] = f"{sandbox.parent / 'bin'}{os.pathsep}{env.get('PATH', '')}"
        command = ["bash", str(launch), str(input_path), str(output_path)]
        proc = subprocess.run(
            isolation_prefix() + command,
            cwd=sandbox,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            preexec_fn=_limit_cpu,
        )
    if proc.returncode != 0:
        tail = log_path.read_text(errors="replace")[-600:]
        raise RunFailure(f"retriever exited with code {proc.returncode}: {tail}")
    if not output_path.is_file():
        raise RunFailure("retriever wrote no output file")


def parse_rows(output_path: Path, data: dict) -> dict[str, list[str]]:
    questions = data["_questions"]
    entries = data["_entries"]
    rankings: dict[str, list[str]] = {}
    # Bound parsing and turn every malformed artifact into a complete failure
    # vector. Extra fields may exist but can never supply a scored number.
    try:
        if output_path.stat().st_size > max(1_048_576, len(questions) * 16_384):
            raise RunFailure("retriever output exceeds the JSONL size limit")
        output_text = output_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise RunFailure(f"cannot read retriever output: {exc}") from exc
    for line_no, line in enumerate(output_text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except (ValueError, RecursionError) as exc:
            raise RunFailure(f"line {line_no}: invalid JSON") from exc
        if not isinstance(row, dict):
            raise RunFailure(f"line {line_no}: row is not an object")
        qid = row.get("question_id")
        ids = row.get("retrieved_entry_ids")
        if not isinstance(qid, str) or qid not in questions:
            raise RunFailure(f"line {line_no}: unknown question_id {qid!r}")
        if qid in rankings:
            raise RunFailure(f"duplicate row for question {qid}")
        if not isinstance(ids, list) or not all(isinstance(x, str) for x in ids):
            raise RunFailure(f"question {qid}: retrieved_entry_ids must be a list of strings")
        if len(ids) > MAX_RETRIEVED:
            raise RunFailure(f"question {qid}: {len(ids)} entries returned, budget is {MAX_RETRIEVED}")
        if len(set(ids)) != len(ids):
            raise RunFailure(f"question {qid}: duplicate entry ids")
        conv_id = questions[qid]["conversation_id"]
        for entry_id in ids:
            entry = entries.get(entry_id)
            if entry is None:
                raise RunFailure(f"question {qid}: unknown entry id {entry_id!r}")
            if entry["conversation_id"] != conv_id:
                raise RunFailure(f"question {qid}: entry {entry_id} belongs to another conversation")
        rankings[qid] = ids
    missing = [qid for qid in questions if qid not in rankings]
    if missing:
        raise RunFailure(f"{len(missing)} questions have no row (e.g. {missing[0]})")
    return rankings


def answer_terms(answer: str) -> set[str]:
    terms = set(tokens(answer))
    content = terms - ANSWER_STOPWORDS
    return content or terms


def per_question(rankings: dict[str, list[str]], data: dict) -> list[dict]:
    entries = data["_entries"]
    records = []
    for q in data["questions"]:
        ids = rankings[q["question_id"]]
        gold = set(q["evidence_entry_ids"])
        context = [render(entries[entry_id]) for entry_id in ids]
        context_tokens = [tokens(text) for text in context]
        delivered = set().union(*context_tokens) if context_tokens else set()
        wanted = answer_terms(q["answer"])
        records.append(
            {
                "question_id": q["question_id"],
                "category": q["category"],
                "evidence_recall": len(gold.intersection(ids)) / len(gold),
                "hit_at_1": float(bool(ids) and ids[0] in gold),
                "answer_token_recall": len(wanted & delivered) / len(wanted) if wanted else 0.0,
                "context_tokens": sum(len(t) for t in context_tokens),
            }
        )
    return records


def aggregate(records: list[dict]) -> tuple[dict[str, float], dict[str, float]]:
    n = len(records)
    by_category: dict[str, list[float]] = defaultdict(list)
    for record in records:
        by_category[record["category"]].append(record["evidence_recall"])
    category_recall = {cat: 100.0 * sum(v) / len(v) for cat, v in sorted(by_category.items())}
    metrics = {
        "evidence_recall_at_10": 100.0 * sum(r["evidence_recall"] for r in records) / n,
        "evidence_hit_at_1": 100.0 * sum(r["hit_at_1"] for r in records) / n,
        "answer_token_recall": 100.0 * sum(r["answer_token_recall"] for r in records) / n,
        "worst_category_recall": min(category_recall.values()),
        "avg_context_tokens": sum(r["context_tokens"] for r in records) / n,
    }
    return metrics, category_recall


def failed_metrics(data: dict) -> dict[str, float]:
    """Worst scores a run can get: zero quality, maximum context the budget allows."""
    by_conv: dict[str, list[int]] = defaultdict(list)
    for entry in data["_entries"].values():
        by_conv[entry["conversation_id"]].append(len(tokens(render(entry))))
    worst_context = {
        conv: sum(sorted(lengths, reverse=True)[:MAX_RETRIEVED]) for conv, lengths in by_conv.items()
    }
    avg_worst = sum(worst_context[q["conversation_id"]] for q in data["questions"]) / len(data["questions"])
    return {
        "evidence_recall_at_10": 0.0,
        "evidence_hit_at_1": 0.0,
        "answer_token_recall": 0.0,
        "worst_category_recall": 0.0,
        "avg_context_tokens": avg_worst,
    }


def score_artifacts(paths: list[Path], data: dict) -> dict:
    results: dict[str, dict[str, float]] = {}
    status: dict[str, dict] = {}
    categories: dict[str, dict[str, float]] = {}
    for path in paths:
        name = path.stem if path.stem != "retrieval_results" else path.parent.name
        try:
            records = per_question(parse_rows(path, data), data)
            metrics, category_recall = aggregate(records)
            if metrics["evidence_recall_at_10"] < MIN_EVIDENCE_RECALL:
                raise RunFailure(f"evidence_recall_at_10 below the task floor {MIN_EVIDENCE_RECALL}")
            results[name], categories[name], status[name] = metrics, category_recall, {"valid": True}
        except RunFailure as exc:
            results[name], status[name] = failed_metrics(data), {"valid": False, "reason": str(exc)}
    return {"experiments": {EXPERIMENT: {"slice": SLICE, "results": results, "_status": status, "_category_recall": categories}}}


def fixed_comparisons(data: dict) -> dict:
    """Comparison procedures are frozen here, never imported from a method.

    These diagnostics are not leaderboard entries; only results are ranked.
    """
    import importlib.util
    path = Path(__file__).with_name("fixed_baselines.py")
    spec = importlib.util.spec_from_file_location("fixed_memory_baselines", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    comparison = {}
    for name, rankings in module.rankings(data, MAX_RETRIEVED).items():
        metrics, _ = aggregate(per_question(rankings, data))
        comparison[name] = metrics
    lengths = {
        c["conversation_id"]: sum(len(tokens(render(e))) for e in c["entries"])
        for c in data["conversations"]
    }
    comparison["full_history_context_tokens"] = (
        sum(lengths[q["conversation_id"]] for q in data["questions"]) / len(data["questions"])
    )
    return comparison


def discover(registry: Path) -> list[Path]:
    return sorted(path for path in registry.glob("*.sh") if path.is_file())


def evaluate(scripts: list[Path], data: dict, per_question_dir: Path | None, keep_dir: Path | None) -> dict:
    names = [script.stem for script in scripts]
    if len(set(names)) != len(names):
        raise SystemExit(f"retriever names must be unique: {names}")
    results: dict[str, dict[str, float]] = {}
    status: dict[str, dict] = {}
    categories: dict[str, dict[str, float]] = {}
    comparisons = fixed_comparisons(data)
    with tempfile.TemporaryDirectory(prefix="memory_eval_") as tmp:
        tmp_path = Path(tmp)
        input_path = tmp_path / "memory_input.json"
        input_path.write_text(json.dumps(public_input(data)))
        sandbox = build_sandbox(tmp_path)
        isolate, isolation_note = probe_isolation()
        print(f"[{SLICE}] isolation: {isolation_note}", file=sys.stderr)
        for script in scripts:
            name = script.stem
            output_path = tmp_path / f"{name}.jsonl"
            log_path = tmp_path / f"{name}.log"
            try:
                if not isolate:
                    raise RunFailure(f"required test-file isolation unavailable: {isolation_note}")
                run_retriever(script, input_path, output_path, sandbox, log_path, isolate)
                rankings = parse_rows(output_path, data)
                records = per_question(rankings, data)
                metrics, category_recall = aggregate(records)
                if metrics["evidence_recall_at_10"] < MIN_EVIDENCE_RECALL:
                    raise RunFailure(
                        f"evidence_recall_at_10 {metrics['evidence_recall_at_10']:.2f} is below the "
                        f"task floor {MIN_EVIDENCE_RECALL}",
                        metrics,
                    )
                results[name] = metrics
                categories[name] = category_recall
                status[name] = {"valid": True}
                if per_question_dir is not None:
                    per_question_dir.mkdir(parents=True, exist_ok=True)
                    (per_question_dir / f"{name}.jsonl").write_text(
                        "".join(json.dumps(r) + "\n" for r in records)
                    )
            except (RunFailure, OSError, UnicodeError) as exc:
                results[name] = failed_metrics(data)
                status[name] = {"valid": False, "reason": str(exc.args[0])}
                if len(exc.args) > 1:
                    status[name]["unscored_raw_metrics"] = exc.args[1]
                print(f"[{SLICE}] {name}: FAILED - {exc}", file=sys.stderr)
            if keep_dir is not None:
                keep_dir.mkdir(parents=True, exist_ok=True)
                for path in (output_path, log_path):
                    if path.is_file():
                        (keep_dir / path.name).write_bytes(path.read_bytes())
            print(f"[{SLICE}] {name}: {json.dumps(results[name])}", file=sys.stderr)
    category_counts: dict[str, int] = defaultdict(int)
    for q in data["questions"]:
        category_counts[q["category"]] += 1
    return {
        "slice": SLICE,
        "experiments": {
            EXPERIMENT: {
                "slice": SLICE,
                "split": {
                    "retriever_isolation": isolation_note,
                    "name": "locomo_train_conversations_v3",
                    "conversations": [c["conversation_id"] for c in data["conversations"]],
                    "question_count": len(data["questions"]),
                    "category_counts": dict(sorted(category_counts.items())),
                    "max_retrieved": MAX_RETRIEVED,
                    "min_evidence_recall": MIN_EVIDENCE_RECALL,
                },
                "results": results,
                "_status": status,
                "_category_recall": categories,
                "_fixed_comparisons": comparisons,
            }
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("retrievers", nargs="*", help="retriever scripts (default: every scripts/retrievers/*.sh)")
    parser.add_argument("--registry", default=str(ROOT / "scripts" / "retrievers"))
    parser.add_argument("--output", default=str(ROOT / "scoring" / "scores_train.json"))
    parser.add_argument("--data", default=str(DATA_PATH))
    parser.add_argument(
        "--artifacts",
        nargs="*",
        default=None,
        help="score saved retrieval JSONL files (method name = file stem) instead of running retrievers",
    )
    parser.add_argument("--per-question-dir", default=None, help="optional per-question dump for paired analysis")
    parser.add_argument("--keep-outputs", default=None, help="optional directory to keep raw retriever outputs")
    args = parser.parse_args()

    data = load_dataset(Path(args.data))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.artifacts:
        scores = score_artifacts([Path(p) for p in args.artifacts], data)
        output.write_text(json.dumps(scores, indent=2, sort_keys=True) + "\n")
        return
    scripts = [Path(p) for p in args.retrievers] if args.retrievers else discover(Path(args.registry))
    if not scripts:
        raise SystemExit("no retrievers found")
    scores = evaluate(
        scripts,
        data,
        Path(args.per_question_dir) if args.per_question_dir else None,
        Path(args.keep_outputs) if args.keep_outputs else None,
    )
    output.write_text(json.dumps(scores, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
