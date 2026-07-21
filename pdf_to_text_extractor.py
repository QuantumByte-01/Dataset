#!/usr/bin/env python
"""
pdf_to_text_extractor.py

Extract text from the FW-VTOL source PDF(s) in input_pdfs/ and chunk it by
section so downstream generation agents each receive a grounded slice rather
than the whole document.

Outputs (under extracted_text/):
  <stem>.full.txt          - full plain text, page markers preserved
  <stem>.pages.jsonl       - one JSON object per page {page, text}
  chunks/<stem>__NN_<slug>.txt   - section-level chunks
  chunks/_index.json       - manifest of all chunks (stem, section title, chars)

Usage:  python pdf_to_text_extractor.py
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

import fitz  # PyMuPDF

ROOT = Path(__file__).resolve().parent
IN_DIR = ROOT / "input_pdfs"
OUT_DIR = ROOT / "extracted_text"
CHUNK_DIR = OUT_DIR / "chunks"

# Heuristic: numbered section headers like "3", "3.1", "3.1.2" followed by a Title.
SECTION_RE = re.compile(r"^\s{0,3}(\d{1,2}(?:\.\d{1,2}){0,3})\.?\s+([A-Z][^\n]{2,80})\s*$")
# Also catch all-caps / title-case unnumbered headers (Abstract, Introduction, etc.)
NAMED_RE = re.compile(
    r"^\s{0,3}(Abstract|Introduction|Conclusion[s]?|References|Nomenclature|"
    r"Acknowledial?gements?|Appendix[^\n]{0,40})\s*$",
    re.IGNORECASE,
)


def slugify(s: str, n: int = 40) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_").lower()
    return s[:n] or "section"


def extract_pdf(pdf_path: Path):
    doc = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc):
        pages.append({"page": i + 1, "text": page.get_text("text")})
    doc.close()
    return pages


def write_full(stem: str, pages):
    full = OUT_DIR / f"{stem}.full.txt"
    with full.open("w", encoding="utf-8") as f:
        for p in pages:
            f.write(f"\n\n===== PAGE {p['page']} =====\n\n")
            f.write(p["text"])
    with (OUT_DIR / f"{stem}.pages.jsonl").open("w", encoding="utf-8") as f:
        for p in pages:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")


def chunk_by_section(stem: str, pages):
    """Split the concatenated body into section-level chunks using header regex."""
    lines = []
    for p in pages:
        for ln in p["text"].splitlines():
            lines.append((p["page"], ln))

    chunks = []  # list of dict(title, start_page, lines[])
    cur = {"title": "front_matter", "page": pages[0]["page"] if pages else 1, "lines": []}
    for page, ln in lines:
        m = SECTION_RE.match(ln) or NAMED_RE.match(ln)
        if m and len(ln.strip()) < 90:
            # start a new chunk
            if cur["lines"]:
                chunks.append(cur)
            title = ln.strip()
            cur = {"title": title, "page": page, "lines": []}
        else:
            cur["lines"].append(ln)
    if cur["lines"]:
        chunks.append(cur)

    # Merge tiny chunks (< 300 chars) into the previous to avoid header noise.
    merged = []
    for c in chunks:
        body = "\n".join(c["lines"]).strip()
        if merged and len(body) < 300:
            merged[-1]["lines"].append(c["title"])
            merged[-1]["lines"].extend(c["lines"])
        else:
            merged.append(c)

    manifest = []
    for idx, c in enumerate(merged):
        body = "\n".join(c["lines"]).strip()
        if not body:
            continue
        slug = slugify(c["title"])
        fname = f"{stem}__{idx:02d}_{slug}.txt"
        (CHUNK_DIR / fname).write_text(
            f"# SOURCE: {stem}\n# SECTION: {c['title']}\n# START_PAGE: {c['page']}\n\n{body}\n",
            encoding="utf-8",
        )
        manifest.append(
            {"file": fname, "source": stem, "section": c["title"],
             "start_page": c["page"], "chars": len(body)}
        )
    return manifest


def main():
    OUT_DIR.mkdir(exist_ok=True)
    CHUNK_DIR.mkdir(exist_ok=True)
    pdfs = sorted(IN_DIR.glob("*.pdf"))
    if not pdfs:
        print("No PDFs in input_pdfs/", file=sys.stderr)
        sys.exit(1)
    all_manifest = []
    for pdf in pdfs:
        stem = re.sub(r"[^A-Za-z0-9]+", "_", pdf.stem)[:60].strip("_")
        print(f"[extract] {pdf.name} -> stem={stem}")
        pages = extract_pdf(pdf)
        write_full(stem, pages)
        man = chunk_by_section(stem, pages)
        print(f"          {len(pages)} pages, {len(man)} chunks")
        all_manifest.extend(man)
    (CHUNK_DIR / "_index.json").write_text(
        json.dumps(all_manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    total_chars = sum(m["chars"] for m in all_manifest)
    print(f"[done] {len(all_manifest)} chunks total, {total_chars:,} chars -> {CHUNK_DIR}")


if __name__ == "__main__":
    main()
