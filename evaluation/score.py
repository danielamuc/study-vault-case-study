"""Score an LLM-as-judge run: mean score per judge and mode, judge agreement, retrieval hit rate.

Usage: python3 evaluation/score.py <run folder>   (reads judge_*.json and answers_*.json in that folder)
Scores: 2 = correct and supported, 1 = partly correct or incomplete, 0 = wrong, invented or missing.
"""
import json
import sys
from collections import Counter
from pathlib import Path

EVAL = Path(__file__).parent
HERE = Path(sys.argv[1]) if len(sys.argv) > 1 else EVAL


def kappa(a, b):
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    expected = sum(ca[k] * cb[k] for k in set(a) | set(b)) / n ** 2
    return 1.0 if expected == 1 else (observed - expected) / (1 - expected)


judges = {p.stem.removeprefix("judge_"): json.loads(p.read_text()) for p in sorted(HERE.glob("judge_*.json"))}
modes = sorted({s["mode"] for j in judges.values() for s in j["scores"]})
lines = ["# LLM-as-judge results", ""]
for mode in modes:
    per_judge = {name: {s["id"]: s["score"] for s in j["scores"] if s["mode"] == mode} for name, j in judges.items()}
    ids = sorted(next(iter(per_judge.values())))
    lines.append(f"## Mode: {mode}")
    for name, scores in per_judge.items():
        total = sum(scores[i] for i in ids)
        lines.append(f"- judge {name}: {total}/{2 * len(ids)} points ({100 * total / (2 * len(ids)):.0f}%), "
                     f"fully correct {sum(scores[i] == 2 for i in ids)}/{len(ids)}")
    names = list(per_judge)
    if len(names) == 2:
        a, b = ([per_judge[n][i] for i in ids] for n in names)
        lines.append(f"- agreement: {sum(x == y for x, y in zip(a, b))}/{len(ids)} exact, Cohen's kappa {kappa(a, b):.2f}")
        low = [i for i in ids if min(per_judge[n][i] for n in names) < 2]
        lines.append(f"- questions below full marks for at least one judge: {', '.join(low) or 'none'}")
    lines.append("")
answers = HERE / "answers_vault.json"
if answers.exists():
    expected = json.loads((EVAL / "expected_cards.json").read_text())
    read = {a["id"]: set(a.get("files_read", [])) for a in json.loads(answers.read_text())["answers"]}
    asked = [i for i in expected if i in read]
    hits = [i for i in asked if read.get(i, set()) & set(expected[i])]
    mean_files = sum(len(v) for v in read.values()) / len(read)
    lines += ["## Retrieval (vault mode)",
              f"- hit rate: {len(hits)}/{len(asked)} questions opened at least one expected card",
              f"- misses: {', '.join(i for i in asked if i not in hits) or 'none'}",
              f"- mean files opened per question: {mean_files:.1f}", ""]
(HERE / "results.md").write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
