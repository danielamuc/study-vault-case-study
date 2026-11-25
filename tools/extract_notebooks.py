"""Separate Daniela's own work from course text in Jupyter notebooks kept in a git clone.

Usage: python3 -I tools/extract_notebooks.py <out_dir> <repo_root>

The last commit (HEAD) holds the teacher's version; the working copy holds her answers.
For every notebook the working copy changed, it writes <out_dir>/<notebook>.md with:
- the outline (all markdown headings), so readers see what the notebook teaches;
- her cells (new or changed compared with HEAD), each with the teacher cell before it as context,
  and a short text of the cell output.
"""
import json
import subprocess
import sys
from pathlib import Path

CONTEXT, OUTPUT = 600, 800


def text(cell):
    return "".join(cell.get("source", "")).strip()


def output_text(cell):
    parts = []
    for out in cell.get("outputs", []):
        parts.append("".join(out.get("text", "")) or "".join(out.get("data", {}).get("text/plain", "")))
    return "\n".join(p for p in parts if p).strip()[:OUTPUT]


def changed_notebooks(repo):
    names = subprocess.run(["git", "-C", repo, "diff", "--name-only", "HEAD"], capture_output=True, text=True).stdout
    return [n for n in names.splitlines() if n.endswith(".ipynb")]


def extract(repo, rel, out_dir):
    original = subprocess.run(["git", "-C", repo, "show", f"HEAD:{rel}"], capture_output=True, text=True).stdout
    teacher = {text(c) for c in json.loads(original)["cells"]} if original else set()
    cells = json.loads((Path(repo) / rel).read_text(encoding="utf-8"))["cells"]
    outline = [line for c in cells if c["cell_type"] == "markdown"
               for line in text(c).splitlines() if line.startswith("#")]
    parts = [f"# {Path(rel).stem}", "", f"Source: {Path(repo) / rel}", "", "## Outline", "", *outline, "", "## My work", ""]
    mine = 0
    for i, cell in enumerate(cells):
        if not text(cell) or text(cell) in teacher:
            continue
        mine += 1
        before = next((text(c) for c in reversed(cells[:i]) if text(c) in teacher), "")
        parts += [f"### Cell {i} ({cell['cell_type']})", "", f"Context (teacher): {before[:CONTEXT]}", "",
                  "Mine:", "```", text(cell), "```"]
        if output_text(cell):
            parts += ["Output:", "```", output_text(cell), "```"]
        parts.append("")
    (out_dir / f"{Path(rel).stem}.md").write_text("\n".join(parts), encoding="utf-8")
    return mine


def main():
    out_dir, repo = Path(sys.argv[1]).resolve(), sys.argv[2]
    out_dir.mkdir(parents=True, exist_ok=True)
    for rel in changed_notebooks(repo):
        print(f"{extract(repo, rel, out_dir):4d} cells of mine  {rel}")


if __name__ == "__main__":
    main()
