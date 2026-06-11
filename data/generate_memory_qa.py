#!/usr/bin/env python3
"""Generate a small long-memory QA benchmark for retrieval evaluation.

The paper evaluates on LoCoMo/LongMemEval, but the reusable gym needs a
portable dataset. This generator creates multi-session conversational memories
with distractors, paraphrased questions, and labeled answer-bearing entries.
It is method-agnostic and belongs in data/.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


PEOPLE = [
    "Alex", "Blair", "Casey", "Devon", "Elliot", "Finley", "Gray", "Harper",
    "Indigo", "Jordan", "Kai", "Logan", "Morgan", "Nico", "Parker", "Quinn",
]
PROJECTS = [
    "aurora dashboard", "cedar migration", "delta audit", "ember rollout",
    "falcon parser", "grove planner", "harbor release", "iris prototype",
]
COMPANIES = [
    "Vega Corp", "Northwind Labs", "Orion Health", "Summit Retail",
    "Cobalt Finance", "Nimbus Transit", "Atlas Foods", "Helio Energy",
]
TOOLS = [
    "TimescaleDB", "DuckDB", "Redis Streams", "OpenSearch", "PostGIS",
    "Ray Serve", "Airflow", "FastAPI",
]
TIMES = [
    "after the April planning review", "before the budget freeze",
    "during the Wednesday incident call", "after the customer migration",
    "before the Friday demo", "during the security review",
]
PREFERENCES = [
    "prefers concise bullet updates", "wants diagrams before code",
    "avoids Friday deployments", "requires EU-only storage",
    "likes owner and deadline tables", "needs audit logs preserved",
]


QUESTION_TEMPLATES = [
    "Which tool did {person} choose for the {project} at {company}?",
    "For {company}'s {project}, what technology did {person} settle on?",
    "What should be used by {person} on the {project} for {company}?",
]


def _entry(entry_id: str, session: int, speaker: str, text: str) -> dict:
    ordinal = int(entry_id.rsplit("e", 1)[-1])
    return {
        "entry_id": entry_id,
        "session": session,
        "speaker": speaker,
        "timestamp": f"2026-02-{session + 1:02d}T09:{ordinal % 60:02d}:00Z",
        "text": text,
    }


def build_dataset(
    seed: int,
    conversations: int,
    facts_per_conversation: int,
    distractors_per_fact: int,
    ambiguous_decoys_per_fact: int,
) -> dict:
    rng = random.Random(seed)
    conversations_out = []
    questions_out = []

    fact_counter = 0
    for conv_idx in range(conversations):
        entries = []
        used = set()
        for fact_idx in range(facts_per_conversation):
            person = PEOPLE[(conv_idx + fact_idx) % len(PEOPLE)]
            project = PROJECTS[(conv_idx * 3 + fact_idx) % len(PROJECTS)]
            company = COMPANIES[(conv_idx * 5 + fact_idx) % len(COMPANIES)]
            tool = TOOLS[(conv_idx * 7 + fact_idx * 2) % len(TOOLS)]
            time_phrase = TIMES[(conv_idx + fact_idx * 2) % len(TIMES)]
            preference = PREFERENCES[(conv_idx * 2 + fact_idx) % len(PREFERENCES)]
            if (person, project, company) in used:
                continue
            used.add((person, project, company))

            session = 1 + (fact_idx % 8)
            entry_id = f"c{conv_idx}_e{len(entries)}"
            text = (
                f"{person} said that {time_phrase}, the {project} for {company} "
                f"would use {tool}. {person} also {preference}."
            )
            entries.append(_entry(entry_id, session, "assistant", text))

            for distractor_idx in range(distractors_per_fact):
                other_tool = TOOLS[(TOOLS.index(tool) + distractor_idx + 3) % len(TOOLS)]
                other_company = COMPANIES[(COMPANIES.index(company) + distractor_idx + 2) % len(COMPANIES)]
                other_project = PROJECTS[(PROJECTS.index(project) + distractor_idx + 3) % len(PROJECTS)]
                distractor_id = f"c{conv_idx}_e{len(entries)}"
                distractor = (
                    f"In a separate note, {person} reviewed {other_project} for "
                    f"{other_company} and mentioned {other_tool}, but no decision was made."
                )
                entries.append(_entry(distractor_id, session, "user", distractor))

            # Same-entity decoys make retrieval meaningfully harder: the entry
            # shares the question's person/project/company but explicitly says
            # the alternate tool was only considered, not chosen.
            for decoy_idx in range(ambiguous_decoys_per_fact):
                other_tool = TOOLS[(TOOLS.index(tool) + decoy_idx + 1) % len(TOOLS)]
                decoy_id = f"c{conv_idx}_e{len(entries)}"
                decoy = (
                    f"{person} later revisited the {project} for {company} and considered "
                    f"{other_tool}, but the team did not change the original decision."
                )
                entries.append(_entry(decoy_id, session + 1, "assistant", decoy))

            question = rng.choice(QUESTION_TEMPLATES).format(
                person=person, project=project, company=company
            )
            questions_out.append(
                {
                    "question_id": f"q{fact_counter}",
                    "conversation_id": f"conv_{conv_idx}",
                    "question": question,
                    "answer": tool,
                    "gold_entry_ids": [entry_id],
                    "category": ["single_hop", "multi_hop", "temporal"][fact_idx % 3],
                }
            )
            fact_counter += 1

        # Add unrelated chatter so retrieval has to filter over long histories.
        for noise_idx in range(facts_per_conversation):
            person = rng.choice(PEOPLE)
            entries.append(
                _entry(
                    f"c{conv_idx}_e{len(entries)}",
                    9 + noise_idx % 4,
                    rng.choice(["user", "assistant"]),
                    f"{person} asked for a weekly status summary and a reminder about travel receipts.",
                )
            )
        conversations_out.append({"conversation_id": f"conv_{conv_idx}", "entries": entries})

    return {"conversations": conversations_out, "questions": questions_out}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/memory_qa.json")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--conversations", type=int, default=8)
    parser.add_argument("--facts-per-conversation", type=int, default=9)
    parser.add_argument("--distractors-per-fact", type=int, default=3)
    parser.add_argument("--ambiguous-decoys-per-fact", type=int, default=2)
    args = parser.parse_args()

    data = build_dataset(
        seed=args.seed,
        conversations=args.conversations,
        facts_per_conversation=args.facts_per_conversation,
        distractors_per_fact=args.distractors_per_fact,
        ambiguous_decoys_per_fact=args.ambiguous_decoys_per_fact,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n")


if __name__ == "__main__":
    main()
