"""Prepare lecture PDFs for reading by agents.

Usage: python3 -I tools/extract.py [--light] <out_dir> <pdf or folder> [...]

For each deck it writes <out_dir>/<deck>/pages.md and, where needed, page images.
- Copies of the same deck ("with my notes", "-annotated", "(1)") are reduced to the copy with the most annotations.
- Animation build steps are dropped: a page whose text lines all appear on the next page.
- A page is rendered as an image when its text is thin, when a large picture covers it,
  or when it carries one of Daniela's annotations. Text alone loses that content.
- .pptx files: only the slide text is extracted (no images).
- --light: for image-heavy decks without annotations. Only text-thin or annotated pages get an
  image, at 72 dpi. Full-page backgrounds never count as pictures.
"""
import json
import re
import sys
import zipfile
from pathlib import Path

import pymupdf

DPI = 110
LIGHT_DPI = 72
BACKGROUND = 0.9         # a picture this large is a slide background
THIN_TEXT = 200          # characters
LARGE_PICTURE = 0.3      # share of the page area


def deck_key(path):
    return re.sub(r"\s*(\(?with my notes\)?|[-_ ]annotated|_notes|\(\d+\))", "", path.stem, flags=re.I).strip().lower()


def annotation_count(path):
    if path.suffix != ".pdf":
        return 0
    return sum(len(list(page.annots() or [])) for page in pymupdf.open(path))


def pick_decks(inputs):
    """One file per lecture: among copies of the same deck, the one with the most annotations."""
    pdfs = []
    for item in map(Path, inputs):
        pdfs += sorted(list(item.rglob("*.pdf")) + list(item.rglob("*.pptx"))) if item.is_dir() else [item]
    chosen = {}
    for pdf in pdfs:
        key = deck_key(pdf)
        if key not in chosen or annotation_count(pdf) > annotation_count(chosen[key]):
            chosen[key] = pdf
    return chosen


def lines(text):
    return {line.strip() for line in text.splitlines() if line.strip()}


def annotations(page):
    found = []
    for annot in page.annots() or []:
        kind = annot.type[1]
        note = (annot.info.get("content") or "").strip()
        marked = ""
        if kind in ("Highlight", "Underline", "StrikeOut", "Squiggly"):
            marked = page.get_textbox(annot.rect).strip()
        found.append({"kind": kind, "note": note, "marked_text": marked})
    return found


def picture_share(page):
    area = page.rect.width * page.rect.height
    shares = [pymupdf.Rect(info["bbox"]).get_area() / area
              for info in page.get_image_info() if info.get("bbox")] if area else []
    return sum(s for s in shares if s < BACKGROUND)


def extract_pptx(pptx, out):
    with zipfile.ZipFile(pptx) as z:
        slides = sorted((n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
                        key=lambda n: int(re.search(r"\d+", n.rsplit("/", 1)[1]).group()))
        texts = [" ".join(re.findall(r"<a:t>([^<]*)</a:t>", z.read(n).decode("utf-8"))) for n in slides]
    out.mkdir(parents=True, exist_ok=True)
    parts = [f"# {pptx.name}\n\nSource: {pptx}\nSlides: {len(texts)} (text only)\n"]
    parts += [f"\n## Page {i + 1}\n\n{t or '(no text)'}" for i, t in enumerate(texts)]
    (out / "pages.md").write_text("\n".join(parts), encoding="utf-8")
    return {"source": str(pptx), "pages": len(texts), "kept": len(texts), "images": 0, "annotated_pages": 0}


def extract(pdf, out, light):
    if pdf.suffix == ".pptx":
        return extract_pptx(pdf, out)
    doc = pymupdf.open(pdf)
    texts = [page.get_text().strip() for page in doc]
    out.mkdir(parents=True, exist_ok=True)
    stats = {"source": str(pdf), "pages": len(doc), "kept": 0, "images": 0, "annotated_pages": 0}
    parts = [f"# {pdf.name}\n\nSource: {pdf}\nPages in deck: {len(doc)}\n"]
    for i, page in enumerate(doc):
        notes = annotations(page)
        is_build_step = (i + 1 < len(doc) and texts[i]
                         and lines(texts[i]) <= lines(texts[i + 1]) and not notes)
        if is_build_step:
            continue
        stats["kept"] += 1
        block = [f"\n## Page {i + 1}\n", texts[i] or "(no text)"]
        pictures = not light and picture_share(page) > LARGE_PICTURE
        if len(texts[i]) < THIN_TEXT or pictures or notes:
            image = out / f"page-{i + 1:03d}.png"
            page.get_pixmap(dpi=LIGHT_DPI if light else DPI).save(image)
            stats["images"] += 1
            block.append(f"\n[image: {image}]")
        if notes:
            stats["annotated_pages"] += 1
            block.append("\nDaniela's annotations on this page:\n" + "\n".join(
                f"- {n['kind']}: {n['note'] or ''} {('(marked: ' + n['marked_text'][:200] + ')') if n['marked_text'] else ''}".rstrip()
                for n in notes))
        parts.append("\n".join(block))
    (out / "pages.md").write_text("\n".join(parts), encoding="utf-8")
    return stats


def main():
    args = sys.argv[1:]
    light = "--light" in args
    args = [a for a in args if a != "--light"]
    out_dir, inputs = Path(args[0]).resolve(), args[1:]
    report = [extract(pdf, out_dir / re.sub(r"[^a-z0-9]+", "-", key).strip("-"), light)
              for key, pdf in pick_decks(inputs).items()]
    (out_dir / "extract_stats.json").write_text(json.dumps(report, indent=2))
    for s in report:
        print(f"{s['pages']:4d} pages -> {s['kept']:4d} kept, {s['images']:3d} images, "
              f"{s['annotated_pages']:2d} annotated  {Path(s['source']).name}")


if __name__ == "__main__":
    main()
