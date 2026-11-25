"""Merge reader outputs (concept JSON) into the vault cards.

Usage: python3 -I tools/merge_readers.py <merge.json>

merge.json (one per course, kept in _work/<course>/):
  label          section name for this course on concept cards, e.g. "In Mobile Computing"
  analysis       reader output files (paths relative to the vault)
  decks_dir      folder(s) written by tools/extract.py (maps deck folders to PDF files)
  notebooks_dir  folder searched for "<stem>.ipynb" when a reader cites a notebook
  overrides      {id: {"rename_to": id} | {"drop": true} | fields to set: title, kind, broader, requires, related}

For an existing card it adds the course section, the sources and new relations.
For a new id it writes a new card. It adds `teaches` links to the module or course cards named in the readers' `modules` tags.
Relations to unknown ids are reported and left out. Run tools/vault.py build afterwards.
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extract import deck_key  # noqa: E402
from vault import VAULT, ROOTS, Card  # noqa: E402

import yaml  # noqa: E402

RELATIONS = ("broader", "requires", "related")


def page_ranges(pages):
    ranges = []
    for p in sorted(set(pages)):
        if ranges and p == ranges[-1][1] + 1:
            ranges[-1][1] = p
        else:
            ranges.append([p, p])
    return ", ".join(str(a) if a == b else f"{a}-{b}" for a, b in ranges)


def to_root(path):
    for root, base in sorted(ROOTS.items(), key=lambda kv: -len(kv[1])):
        if str(path).startswith(base):
            return f"{root}/{str(path)[len(base):].lstrip('/')}"
    raise ValueError(f"no root in roots.json for {path}")


def source_list(found, decks, notebooks_dir):
    pages, notebooks = defaultdict(list), set()
    for c in found:
        for s in c.get("sources", []):
            if s.get("deck") in decks:
                pages[s["deck"]].extend(s.get("pages", []))
            if s.get("notebook"):
                hit = next(Path(notebooks_dir).rglob(f"{s['notebook']}.ipynb"), None)
                if hit:
                    notebooks.add(to_root(hit))
    out = [f"{decks[d]}#p{page_ranges(p)}" if p else decks[d] for d, p in sorted(pages.items())]
    return out + sorted(notebooks)


def link(i):
    return f"[[{i}]]"


def save(card):
    head = yaml.safe_dump(card.meta, sort_keys=False, allow_unicode=True, width=1000)
    card.path.write_text(f"---\n{head}---\n{card.body}", encoding="utf-8")


def main():
    spec = json.loads(Path(sys.argv[1]).read_text())
    overrides = spec.get("overrides", {})
    dirs = spec["decks_dir"] if isinstance(spec["decks_dir"], list) else [spec["decks_dir"]]
    stats = [s for d in dirs for s in json.loads((VAULT / d / "extract_stats.json").read_text())]
    decks = {re.sub(r"[^a-z0-9]+", "-", deck_key(Path(s["source"]))).strip("-"): to_root(s["source"]) for s in stats}

    grouped = defaultdict(list)
    for f in spec["analysis"]:
        for c in json.loads((VAULT / f).read_text())["concepts"]:
            cid = overrides.get(c["id"], {}).get("rename_to", c["id"])
            if not overrides.get(cid, {}).get("drop"):
                grouped[cid].append(c)

    existing = {p.stem for p in (VAULT / "concepts").glob("*.md")}
    known = existing | set(grouped)
    dropped, created, updated = [], [], []
    teaches = defaultdict(set)
    for cid, found in grouped.items():
        fix = overrides.get(cid, {})
        rel = {r: fix[r] if r in fix else sorted({overrides.get(t, {}).get("rename_to", t)
                                                  for c in found for t in c.get(r, [])} - {cid}) for r in RELATIONS}
        for r in RELATIONS:
            dropped += [f"{cid} {r} -> {t}" for t in rel[r] if t not in known]
            rel[r] = [t for t in rel[r] if t in known]
        angles = " ".join(c["course_angle"] for c in found if c.get("course_angle"))
        sources = source_list(found, decks, spec["notebooks_dir"])
        aliases = {a for c in found for a in c.get("aliases", [])}
        for c in found:
            for m in c.get("modules", []):
                teaches[m].add(cid)
        path = VAULT / "concepts" / f"{cid}.md"
        if cid in existing:
            card = Card(path)
            for r in RELATIONS:
                merged = list(dict.fromkeys(card.links(r) + rel[r]))
                if merged:
                    card.meta[r] = [link(t) for t in merged]
            card.meta["sources"] = list(dict.fromkeys(card.sources() + sources))
            new_aliases = sorted(set(card.meta.get("aliases", [])) | aliases - {card.title})
            if new_aliases:
                card.meta["aliases"] = new_aliases
            if angles and f"**{spec['label']}:**" not in card.body:
                card.body = card.body.rstrip() + f"\n\n**{spec['label']}:** {angles}\n"
            save(card)
            updated.append(cid)
            continue
        names = [c.get("name", cid) for c in found]
        meta = {"type": "concept", "id": cid, "title": fix.get("title", max(set(names), key=names.count)),
                "kind": fix.get("kind", found[0].get("kind", "concept"))}
        if aliases - {meta["title"]}:
            meta["aliases"] = sorted(aliases - {meta["title"]})
        for r in RELATIONS:
            if rel[r]:
                meta[r] = [link(t) for t in rel[r]]
        if sources:
            meta["sources"] = sources
        definition = max((c.get("definition", "") for c in found), key=len)
        body = f"# {meta['title']}\n\n**In short:** {definition}\n"
        if angles:
            body += f"\n**{spec['label']}:** {angles}\n"
        path.write_text("---\n" + yaml.safe_dump(meta, sort_keys=False, allow_unicode=True, width=1000)
                        + "---\n" + body, encoding="utf-8")
        created.append(cid)

    for module, ids in teaches.items():
        path = next((p for p in (VAULT / "modules" / f"{module}.md", VAULT / "courses" / f"{module}.md") if p.exists()), None)
        if path is None:
            dropped.append(f"module or course card missing: {module} ({len(ids)} concepts)")
            continue
        card = Card(path)
        card.meta["teaches"] = [link(t) for t in dict.fromkeys(card.links("teaches") + sorted(ids))]
        save(card)
    print(f"created {len(created)}, updated {len(updated)} concept cards; modules: "
          + ", ".join(f"{m} {len(i)}" for m, i in sorted(teaches.items())))
    for d in dropped:
        print("left out:", d)


if __name__ == "__main__":
    main()
