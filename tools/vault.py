"""Study Vault: check the ontology, compute what follows from it, build the generated files.

Usage:
  python3 tools/vault.py check   validate the cards; exit code 1 on errors
  python3 tools/vault.py build   validate, then write the generated block of every card,
                                 index.md, catalog.json, canvases/ and exports/
  python3 tools/vault.py merge <from-id> <into-id>
                                 fold one concept card into another: sections, sources, aliases and
                                 relations move over, every link to <from-id> is rewritten, the card is deleted

The cards are the only source of truth. Everything this script writes can be rebuilt.
"""
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import quote

import yaml

VAULT = Path(__file__).resolve().parent.parent
ROOTS = json.loads((VAULT / "roots.json").read_text())
FOLDERS = {"programme": "programmes", "course": "courses", "module": "modules",
           "concept": "concepts", "project": "projects"}
KINDS = ["domain", "concept", "method", "metric", "tool", "risk"]
# relation -> {source type: allowed target types}
RELATIONS = {
    "part_of": {"course": {"programme"}, "module": {"course"}, "project": {"module", "course"}},
    "teaches": {"module": {"concept"}, "course": {"concept"}},
    "applies": {"project": {"concept"}},
    "broader": {"concept": {"concept"}},
    "requires": {"concept": {"concept"}},
    "related": {"concept": {"concept"}},
}
REQUIRED = {"programme": ["title"], "course": ["title", "part_of"], "module": ["title", "part_of"],
            "concept": ["title", "kind"], "project": ["title", "part_of", "applies"]}
FACT_FIELDS = ["institution", "period", "date", "lecturers", "team", "status"]
GEN_START = "<!-- generated:start (written by tools/vault.py build, do not edit) -->"
GEN_END = "<!-- generated:end -->"


class Card:
    def __init__(self, path):
        self.path = path
        self.type = next((t for t, f in FOLDERS.items() if path.parent.name == f), None)
        text = path.read_text(encoding="utf-8")
        self.meta, self.body = {}, text
        if text.startswith("---\n") and "\n---\n" in text[4:]:
            head, self.body = text[4:].split("\n---\n", 1)
            self.meta = yaml.safe_load(head) or {}
        self.body = self.body.split(GEN_START)[0].rstrip() + "\n"
        self.id = path.stem
        self.title = self.meta.get("title", self.id)

    def links(self, relation):
        values = self.meta.get(relation) or []
        values = [values] if isinstance(values, str) else values
        return [str(v).strip().strip("[]").split("|")[0].strip() for v in values]

    def sources(self):
        return self.meta.get("sources") or []

    def write(self, generated):
        head = yaml.safe_dump(self.meta, sort_keys=False, allow_unicode=True, width=1000)
        self.path.write_text(f"---\n{head}---\n{self.body}\n{GEN_START}\n{generated}\n{GEN_END}\n",
                             encoding="utf-8")


def load():
    cards = {}
    duplicates = []
    for folder in FOLDERS.values():
        for path in sorted((VAULT / folder).glob("*.md")):
            card = Card(path)
            if card.id in cards:
                duplicates.append(card.id)
            cards[card.id] = card
    return cards, duplicates


def resolve_source(source):
    """'STUDIES/a/b.pdf#p13-22' -> (absolute path or URL, page note)."""
    target, _, pages = str(source).partition("#")
    if target.startswith("http"):
        return target, pages
    root, _, rest = target.partition("/")
    base = ROOTS.get(root)
    return (Path(base) / rest if base else None), pages


# ---------- checks ----------

def in_cycle(cards, relation):
    """Cards that can reach themselves along relation."""
    found = []
    for start in cards:
        seen, stack = set(), list(cards[start].links(relation))
        while stack:
            node = stack.pop()
            if node in cards and node not in seen:
                seen.add(node)
                stack.extend(cards[node].links(relation))
        if start in seen:
            found.append(start)
    return found


def check(cards, duplicates, graph):
    errors, warnings = [f"duplicate id: {d}" for d in duplicates], []
    for card in cards.values():
        where = f"{card.path.parent.name}/{card.path.name}"
        if card.meta.get("type") != card.type:
            errors.append(f"{where}: type must be '{card.type}'")
        if card.meta.get("id") != card.id:
            errors.append(f"{where}: id must equal the file name '{card.id}'")
        errors += [f"{where}: missing '{f}'" for f in REQUIRED.get(card.type, []) if not card.meta.get(f)]
        if card.type == "concept" and card.meta.get("kind") not in KINDS:
            errors.append(f"{where}: kind must be one of {KINDS}")
        for relation, allowed in RELATIONS.items():
            targets = card.links(relation)
            if targets and card.type not in allowed:
                errors.append(f"{where}: '{relation}' is not allowed on a {card.type}")
                continue
            for target in targets:
                if target not in cards:
                    errors.append(f"{where}: {relation} -> unknown card '{target}'")
                elif cards[target].type not in allowed[card.type]:
                    errors.append(f"{where}: {relation} -> '{target}' is a {cards[target].type}")
        for source in card.sources():
            path, _ = resolve_source(source)
            if path is None or (isinstance(path, Path) and not path.exists()):
                errors.append(f"{where}: source not found: {source}")
        if card.type == "concept":
            if not card.links("broader") and card.meta.get("kind") != "domain":
                warnings.append(f"{where}: no broader concept")
            info = graph[card.id]
            if not (info["taught_in"] or info["taught_via"] or info["applied_in"] or info["applied_via"]):
                warnings.append(f"{where}: not taught or applied anywhere")
        if card.type == "module" and not card.links("teaches"):
            warnings.append(f"{where}: teaches nothing")
    for relation in ("broader", "requires"):
        errors += [f"cycle in '{relation}' through {c}" for c in in_cycle(cards, relation)]
    return errors, warnings


# ---------- inference ----------

def infer(cards):
    reverse = defaultdict(lambda: defaultdict(list))
    for card in cards.values():
        for relation in RELATIONS:
            for target in card.links(relation):
                if target in cards:
                    reverse[target][relation].append(card.id)

    graph = {}
    for cid, card in cards.items():
        info = {"type": card.type, "title": card.title, "path": str(card.path.relative_to(VAULT)),
                "kind": card.meta.get("kind"), "relations": {r: card.links(r) for r in RELATIONS if card.links(r)},
                "contains": sorted(reverse[cid]["part_of"]), "chain": walk_with_order(cards, cid, "part_of")}
        if card.type == "concept":
            below = walk_with_order(cards, cid, "broader", reverse=reverse)
            info.update(
                ancestors=walk_with_order(cards, cid, "broader"),
                narrower=sorted(reverse[cid]["broader"]),
                descendants=below,
                required_by=sorted(reverse[cid]["requires"]),
                prerequisites=walk_with_order(cards, cid, "requires"),
                taught_in=sorted(reverse[cid]["teaches"]),
                applied_in=sorted(reverse[cid]["applies"]),
            )
            info["taught_via"] = sorted({(d, m) for d in below for m in reverse[d]["teaches"]})
            info["applied_via"] = sorted({(d, p) for d in below for p in reverse[d]["applies"]})
        graph[cid] = info
    for info in graph.values():
        if info["type"] == "concept":
            info["prerequisites"] = [(p, covered(graph[p])) for p in info["prerequisites"]]
        if info["type"] == "project":
            applied = set(info["relations"].get("applies", []))
            areas = {a for c in applied for a in graph[c]["ancestors"]} - applied
            info["areas"] = sorted(areas, key=lambda a: graph[a]["title"])
    return graph


def walk_with_order(cards, start, relation, reverse=None):
    """Breadth-first walk; with reverse, follow the relation backwards."""
    def step(node):
        return reverse[node][relation] if reverse is not None else cards[node].links(relation)
    seen, queue = [], list(step(start))
    while queue:
        node = queue.pop(0)
        if node in cards and node not in seen and node != start:
            seen.append(node)
            queue.extend(step(node))
    return seen


def covered(info):
    return bool(info["taught_in"] or info["applied_in"] or info["taught_via"] or info["applied_via"])


# ---------- generated output ----------

def wl(graph, cid):
    return f"[[{cid}|{graph[cid]['title']}]]"


def source_lines(card):
    lines = []
    for source in card.sources():
        target, pages = resolve_source(source)
        url = target if isinstance(target, str) else "file://" + quote(str(target))
        name = target if isinstance(target, str) else target.name
        lines.append(f"- [{name}]({url})" + (f" {pages}" if pages else ""))
    return lines


def by_kind(graph, ids):
    groups = defaultdict(list)
    for cid in ids:
        groups[graph[cid]["kind"] or "other"].append(wl(graph, cid))
    return [f"- *{kind}*: " + ", ".join(sorted(groups[kind])) for kind in KINDS if groups[kind]]


def generated_block(card, graph):
    info, out = graph[card.id], []

    def add(label, items):
        if items:
            out.append(f"**{label}:** " + ", ".join(items))

    if card.type == "concept":
        add("Taught in", [wl(graph, m) + context(graph, m) for m in info["taught_in"]])
        if not info["taught_in"]:
            add("Taught only through narrower concepts", [f"{wl(graph, d)} in {wl(graph, m)}" for d, m in info["taught_via"]])
        add("Applied in", [wl(graph, p) for p in info["applied_in"]])
        if not info["applied_in"]:
            add("Applied only through narrower concepts", [f"{wl(graph, d)} in {wl(graph, p)}" for d, p in info["applied_via"]])
        add("Broader chain", [" › ".join(wl(graph, a) for a in info["ancestors"])] if info["ancestors"] else [])
        add("Narrower", [wl(graph, n) for n in info["narrower"]])
        add("Required by", [wl(graph, r) for r in info["required_by"]])
        add("All prerequisites", [wl(graph, p) + ("" if ok else " (not covered yet)") for p, ok in info["prerequisites"]])
    elif card.type == "project":
        out.append("**Applies:**")
        out += by_kind(graph, info["relations"].get("applies", []))
        add("Wider areas (inferred)", [wl(graph, a) for a in info["areas"]])
        add("Part of", [wl(graph, c) for c in info["chain"]])
    else:
        add("Part of", [wl(graph, c) for c in info["chain"]])
        add("Contains", [wl(graph, c) for c in info["contains"]])
        taught = info["relations"].get("teaches", [])
        if taught:
            out.append(f"**Teaches ({len(taught)}):**")
            out += by_kind(graph, taught)
    sources = source_lines(card)
    if sources:
        out += ["", "**Where to find more:**"] + sources
    return "\n".join(out)


def context(graph, module):
    chain = graph[module]["chain"]
    return f" ({' › '.join(graph[c]['title'] for c in chain)})" if chain else ""


def write_index(cards, graph):
    lines = ["# Study Vault index", "",
             f"Generated by `tools/vault.py build` on {date.today()}. Do not edit.", "",
             "Legend: ★ applied in a project · • taught in a module · ○ only covered through narrower concepts", "",
             "## Programmes, courses and modules", ""]

    def tree(cid, depth):
        info = graph[cid]
        extra = ""
        if info["type"] == "module":
            extra = f" · {len(info['relations'].get('teaches', []))} concepts"
        lines.append("  " * depth + f"- {wl(graph, cid)} ({info['type']}){extra}")
        for child in sorted(info["contains"], key=lambda c: graph[c]["title"]):
            tree(child, depth + 1)

    for cid in sorted(c for c in graph if graph[c]["type"] == "programme"):
        tree(cid, 0)
    lines += ["", "## Concept map", ""]
    placed = set()

    def mark(info):
        if info["applied_in"]:
            return "★"
        return "•" if info["taught_in"] else "○"

    def concept_tree(cid, depth):
        info = graph[cid]
        others = [graph[b]["title"] for b in info["relations"].get("broader", [])[1:]]
        also = f" (also under: {', '.join(others)})" if others else ""
        lines.append("  " * depth + f"- {mark(info)} {wl(graph, cid)} *{info['kind']}*{also}")
        placed.add(cid)
        children = [n for n in info["narrower"] if cards[n].links("broader")[0] == cid]
        for child in sorted(children, key=lambda c: graph[c]["title"]):
            concept_tree(child, depth + 1)

    roots = [c for c in graph if graph[c]["type"] == "concept" and not cards[c].links("broader")]
    for cid in sorted(roots, key=lambda c: graph[c]["title"]):
        concept_tree(cid, 0)
    (VAULT / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_canvas(module, cards, graph):
    """One Obsidian canvas per module: concept hierarchy in layers, projects at the bottom."""
    taught = set(graph[module]["relations"].get("teaches", []))
    projects = [p for p in graph[module]["contains"] if graph[p]["type"] == "project"]
    applied = {c for p in projects for c in graph[p]["relations"].get("applies", [])}
    concepts = taught | applied
    concepts |= {a for c in concepts for a in graph[c]["ancestors"]}
    level = {}

    def depth(cid):
        if cid not in level:
            parents = [b for b in cards[cid].links("broader") if b in concepts]
            level[cid] = 1 + max((depth(b) for b in parents), default=-1)
        return level[cid]

    rows = defaultdict(list)
    for cid in concepts:
        rows[depth(cid)].append(cid)
    width, height, gap_x, gap_y, per_row = 250, 60, 40, 140, 8
    nodes, position, y = [], {}, 0
    colours = {"taught": "5", "project": "4", "module": "6"}
    nodes.append({"id": module, "type": "text", "text": f"## {wl(graph, module)}", "x": 0, "y": -2 * gap_y,
                  "width": 420, "height": 80, "color": colours["module"]})
    nodes.append({"id": "legend", "type": "text", "x": 480, "y": -2 * gap_y, "width": 640, "height": 120,
                  "text": "**Legend** · cyan: taught in this module · grey: wider area (inferred) · green: project\n"
                          "Arrows: broader (grey) · requires (orange) · applies (green). "
                          "`related` links are in the cards."})
    for lvl in sorted(rows):
        members = sorted(rows[lvl], key=lambda c: (cards[c].links("broader")[:1], graph[c]["title"]))
        for start in range(0, len(members), per_row):
            for i, cid in enumerate(members[start:start + per_row]):
                position[cid] = (i * (width + gap_x), y)
                node = {"id": cid, "type": "text", "text": f"{wl(graph, cid)}\n*{graph[cid]['kind']}*",
                        "x": position[cid][0], "y": y, "width": width, "height": height}
                if cid in taught:
                    node["color"] = colours["taught"]
                nodes.append(node)
            y += gap_y
    for i, pid in enumerate(projects):
        nodes.append({"id": pid, "type": "text", "text": f"### {wl(graph, pid)}", "x": i * (width * 2),
                      "y": y + gap_y // 2, "width": width * 2 - gap_x, "height": 80, "color": colours["project"]})
    edges = []

    def edge(a, b, label, colour=None, sides=("top", "bottom")):
        e = {"id": f"{a}-{label}-{b}", "fromNode": a, "toNode": b, "fromSide": sides[0],
             "toSide": sides[1], "label": label}
        if colour:
            e["color"] = colour
        edges.append(e)

    for cid in concepts:
        for b in cards[cid].links("broader"):
            if b in concepts:
                edge(cid, b, "broader")
        for r in cards[cid].links("requires"):
            if r in concepts:
                edge(cid, r, "requires", "2", ("right", "left"))
    for pid in projects:
        for c in graph[pid]["relations"].get("applies", []):
            edge(pid, c, "applies", "4")
    out = VAULT / "canvases" / f"{module}.canvas"
    out.write_text(json.dumps({"nodes": nodes, "edges": edges}, indent=1), encoding="utf-8")


def write_export(cards, graph, compact=False):
    """One self-contained file for claude.ai Projects, which cannot read local folders.

    compact=True writes a short version: no concept course notes and sources, no module concept lists.
    """
    def plain(cid):
        return graph[cid]["title"]

    parts = [f"# Study Vault: what Daniela studied (export of {date.today()})", "",
             "This file is generated from Daniela's Study Vault, an ontology of her studies at ETH Zurich. "
             "Use it as context when she talks about her studies.", "",
             *(["This is the compact version. The full version (study-vault-context.md) adds what each course said "
                "about each concept and the source pages. In the concept list, modules, projects and broader "
                "concepts are given by id; the sections above give the title for each id.", ""] if compact else []),
             "How to read it:",
             "- A concept is **taught** when a lecture covered it, and **applied** when she used it in a project.",
             "- 'Covered through narrower concepts' means she studied a more specific concept under it.",
             "- If a topic is not in this file, it is not in the vault yet. Say so. Do not guess.",
             "- Source paths point to files on her Mac (STUDIES = Desktop Asus/STUDIES, "
             "ETH_PROJECTS = Documents/Claude/ETH Projects). You cannot open them here.", ""]
    for kind, heading in (("programme", "Programmes"), ("course", "Courses"), ("module", "Modules"),
                          ("project", "Projects")):
        parts += [f"## {heading}", ""]
        for cid in sorted(c for c in graph if graph[c]["type"] == kind):
            body = cards[cid].body.strip()
            parts += [body if body.startswith("#") else f"### {plain(cid)}\n\n{body}", ""]
            info = graph[cid]
            facts = [f"{key}: {', '.join(v) if isinstance(v, list) else v}" for key in FACT_FIELDS
                     if (v := cards[cid].meta.get(key))]
            if compact:
                facts.insert(0, f"id: {cid}")
            if facts:
                parts.append("Facts: " + "; ".join(facts))
            if info["chain"]:
                parts.append("Part of: " + " › ".join(plain(c) for c in info["chain"]))
            for rel in ("teaches", "applies"):
                ids = info["relations"].get(rel, [])
                if ids and not (compact and rel == "teaches"):
                    parts.append(f"{rel.capitalize()}: " + ", ".join(sorted(plain(c) for c in ids)))
            if cards[cid].sources():
                parts.append("Files: " + "; ".join(f"`{s}`" for s in cards[cid].sources()))
            parts.append("")
    parts += ["## Concepts", ""]
    for cid in sorted((c for c in graph if graph[c]["type"] == "concept"), key=plain):
        info = graph[cid]
        name = (lambda c: c) if compact else plain
        facts = [f"kind: {info['kind']}"]
        if compact and cards[cid].links("broader"):
            facts.append("under: " + ", ".join(cards[cid].links("broader")))
        elif info["ancestors"]:
            facts.append("under: " + " › ".join(plain(a) for a in info["ancestors"]))
        if info["taught_in"]:
            facts.append("taught in: " + ", ".join(name(m) for m in info["taught_in"]))
        if info["applied_in"]:
            facts.append("applied in: " + ", ".join(name(p) for p in info["applied_in"]))
        if not info["taught_in"] and info["taught_via"]:
            facts.append("covered through: " + ", ".join(sorted({name(d) for d, _ in info["taught_via"]})))
        sections = {line.split(":**", 1)[0].strip("* "): line.split(":**", 1)[1].strip()
                    for line in cards[cid].body.splitlines() if line.startswith("**") and ":**" in line}
        where = [f"{Path(s.partition('#')[0]).name} {s.partition('#')[2]}".strip() for s in cards[cid].sources()]
        if where and not compact:
            facts.append("source: " + "; ".join(where))
        entry = f"- **{plain(cid)}** ({'; '.join(facts)}). {sections.pop('In short', '')}"
        if not compact:
            entry += "".join(f" {label}: {text}" for label, text in sections.items())
        parts.append(entry)
    name = "study-vault-summary.md" if compact else "study-vault-context.md"
    (VAULT / "exports" / name).write_text("\n".join(parts) + "\n", encoding="utf-8")


def merge(cards, source, target):
    old, new = cards[source], cards[target]
    for relation in ("broader", "requires", "related"):
        links = [t for t in dict.fromkeys(new.links(relation) + old.links(relation)) if t not in (source, target)]
        if links:
            new.meta[relation] = [f"[[{t}]]" for t in links]
    new.meta["sources"] = list(dict.fromkeys(new.sources() + old.sources())) or new.meta.pop("sources", None)
    if not new.meta["sources"]:
        new.meta.pop("sources")
    aliases = sorted(set(new.meta.get("aliases", [])) | set(old.meta.get("aliases", [])) | {old.title} - {new.title})
    new.meta["aliases"] = aliases
    extra = [block for block in old.body.split("\n\n") if block.startswith("**") and block not in new.body]
    new.body = new.body.rstrip() + "".join(f"\n\n{block.strip()}" for block in extra) + "\n"
    head = yaml.safe_dump(new.meta, sort_keys=False, allow_unicode=True, width=1000)
    new.path.write_text(f"---\n{head}---\n{new.body}", encoding="utf-8")
    old.path.unlink()
    for card in VAULT.glob("*/*.md"):
        text = card.read_text(encoding="utf-8")
        if f"[[{source}]]" in text or f"[[{source}|" in text:
            card.write_text(text.replace(f"[[{source}]]", f"[[{target}]]").replace(f"[[{source}|", f"[[{target}|"),
                            encoding="utf-8")
    print(f"merged {source} into {target}")


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else "check"
    cards, duplicates = load()
    if command == "merge":
        merge(cards, sys.argv[2], sys.argv[3])
        cards, duplicates = load()
    graph = infer(cards)
    errors, warnings = check(cards, duplicates, graph)
    for w in warnings:
        print("warning:", w)
    for e in errors:
        print("ERROR:", e)
    counts = defaultdict(int)
    for card in cards.values():
        counts[card.type] += 1
    print(f"{len(cards)} cards ({', '.join(f'{n} {t}' for t, n in counts.items())}); "
          f"{len(errors)} errors, {len(warnings)} warnings")
    if errors:
        sys.exit(1)
    if command == "build":
        for card in cards.values():
            card.write(generated_block(card, graph))
        write_index(cards, graph)
        for module in (c for c in graph if graph[c]["type"] == "module"):
            write_canvas(module, cards, graph)
        (VAULT / "catalog.json").write_text(json.dumps(graph, indent=1, ensure_ascii=False), encoding="utf-8")
        write_export(cards, graph)
        write_export(cards, graph, compact=True)
        print("built: generated blocks, index.md, catalog.json, canvases/, exports/study-vault-context.md")


if __name__ == "__main__":
    main()
