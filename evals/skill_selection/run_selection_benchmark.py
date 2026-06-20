#!/usr/bin/env python3
"""Skill-selection benchmark — does description quality predict whether the
right skill gets picked from a library of candidates?

This is the smallest validation slice for two roadmap ideas at once:
  1. The AI Prompt Builder's tiered question-wizard design (todo.md)
  2. The Own-skill audit's planned-but-undesigned "trigger clarity" check
     (todo.md: "Anthropic-best-practices checks beyond raw spec compliance")

Approach: simulate Claude's skill-relevance matching by giving an LLM the
full corpus's name+description metadata (the only fields the real mechanism
reads) plus a task prompt, and asking which skill it would invoke. Each
corpus task is hand-labeled with the one skill that should be picked, so
this half of the evaluation is objective (precision/recall), not the
subjective "judge the output" half proposed in conversation — that step
isn't built yet; this only tests selection.

IMPORTANT CAVEAT: this approximates Claude's real skill-routing mechanism
via a generic prompt — it is not a guaranteed match to Anthropic's actual
internal routing logic (not introspectable from outside). Read results as
"does this description text discriminate well for an LLM doing relevance
matching," not as a certified prediction of real Claude Code behavior.

Repeats each task N times (default 5) rather than a single shot, mirroring
evals/mcp/behavioral-analysis/scripts/run_determinism_benchmark.py's
repeated-trial approach to LLM call variance.

Usage:
    python evals/skill_selection/run_selection_benchmark.py
    python evals/skill_selection/run_selection_benchmark.py --runs 10
    python evals/skill_selection/run_selection_benchmark.py --output report.json
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))

from skill_scan.core import spec_compliance  # noqa: E402
from skill_scan.core.llm import LLMError, call_llm_sync  # noqa: E402

_HERE = Path(__file__).parent
_CORPUS_DIR = _HERE / "corpus"
_TASKS_FILE = _HERE / "tasks.json"
_CONTROL_SKILLS = {"general-helper", "assistant-tools"}
_DEFAULT_RUNS = 5
_SELECTION_TEMPERATURE = 0.7  # provider default is fine; kept explicit/moderate
_SELECTION_MAX_TOKENS = 60


def load_corpus() -> dict[str, str]:
    """Return {skill_name: description} for every corpus entry."""
    corpus: dict[str, str] = {}
    for folder in sorted(_CORPUS_DIR.iterdir()):
        skill_md = folder / "SKILL.md"
        if not skill_md.exists():
            continue
        meta = spec_compliance.parse_frontmatter(skill_md)
        name = str(meta.get("name") or folder.name)
        corpus[name] = str(meta.get("description") or "")
    return corpus


def load_tasks() -> list[dict]:
    return json.loads(_TASKS_FILE.read_text(encoding="utf-8"))


def build_selection_prompt(corpus: dict[str, str], task_prompt: str) -> str:
    listing = "\n".join(f"- {name}: {desc}" for name, desc in corpus.items())
    return (
        "You are an AI assistant with access to the following skills. "
        "Each skill has a name and a description of when to use it.\n\n"
        f"{listing}\n\n"
        f'User request: "{task_prompt}"\n\n'
        "Which single skill (if any) would you invoke to handle this request? "
        "Respond with ONLY the skill name exactly as listed, or 'none' if no "
        "skill applies. Do not explain your reasoning."
    )


def extract_picks(response: str, corpus: dict[str, str]) -> set[str]:
    """Return the set of corpus skill names that appear in the response text."""
    lowered = response.lower()
    return {name for name in corpus if name.lower() in lowered}


def run_benchmark(runs: int) -> dict:
    corpus = load_corpus()
    tasks = load_tasks()

    per_task: list[dict] = []
    control_trigger_count = 0
    total_trials = 0

    for task in tasks:
        prompt = build_selection_prompt(corpus, task["prompt"])
        expected = task["expected_skill"]
        picks_per_run: list[set[str]] = []

        for _ in range(runs):
            try:
                response = call_llm_sync(
                    prompt,
                    temperature=_SELECTION_TEMPERATURE,
                    max_tokens=_SELECTION_MAX_TOKENS,
                )
            except LLMError as exc:
                print(f"LLM error - aborting: {exc}")
                raise
            picks = extract_picks(response, corpus)
            picks_per_run.append(picks)
            total_trials += 1
            if picks & _CONTROL_SKILLS:
                control_trigger_count += 1

        hits = sum(1 for picks in picks_per_run if expected in picks)
        hit_rate = hits / runs if runs else 0.0
        pick_counts = Counter(name for picks in picks_per_run for name in picks)
        per_task.append(
            {
                "prompt": task["prompt"],
                "expected_skill": expected,
                "hit_rate": hit_rate,
                "hits": hits,
                "runs": runs,
                "pick_distribution": dict(pick_counts),
            }
        )

    overall_accuracy = (
        sum(t["hit_rate"] for t in per_task) / len(per_task) if per_task else 0.0
    )
    control_false_positive_rate = (
        control_trigger_count / total_trials if total_trials else 0.0
    )

    return {
        "runs_per_task": runs,
        "task_count": len(tasks),
        "corpus_size": len(corpus),
        "overall_accuracy": overall_accuracy,
        "control_false_positive_rate": control_false_positive_rate,
        "per_task": per_task,
    }


def print_report(report: dict) -> None:
    print(
        f"\nSkill-selection benchmark — {report['task_count']} tasks x "
        f"{report['runs_per_task']} runs, corpus of {report['corpus_size']} skills\n"
    )
    for t in report["per_task"]:
        flag = "OK" if t["hit_rate"] >= 0.6 else "LOW"
        print(
            f"  [{flag}] {t['hit_rate']:.0%}  {t['expected_skill']:<24}  "
            f"\"{t['prompt'][:60]}\""
        )
        if t["pick_distribution"]:
            dist = ", ".join(
                f"{name}x{count}" for name, count in t["pick_distribution"].items()
            )
            print(f"         picked: {dist}")
    print(f"\nOverall accuracy:            {report['overall_accuracy']:.1%}")
    print(f"Control false-positive rate: {report['control_false_positive_rate']:.1%}")
    print(
        "  (fraction of all trials where a deliberately-vague control skill "
        "got picked — should be near 0%)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=_DEFAULT_RUNS)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    report = run_benchmark(args.runs)
    print_report(report)

    if args.output:
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nFull report written to {args.output}")


if __name__ == "__main__":
    main()
