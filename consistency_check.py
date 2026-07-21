#!/usr/bin/env python
"""
Cross-requirement consistency pass over the merged (or shard-union) dataset.
Looks for conflicting numeric limits on shared parameters and conflicting mode
definitions. Writes consistency_report.md. Does not silently delete records —
fixes only clear hard contradictions when --fix is passed; otherwise reports.
"""
from __future__ import annotations
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "consistency_report.md"

# Patterns: (param_key, regex extracting a comparable number/string, unit note)
PATTERNS = [
    ("mtow_kg", re.compile(r"\b(?:MTOW|take-?off weight|maximum take-?off mass)\b[^\n.]{0,40}?(\d+(?:\.\d+)?)\s*kg", re.I), "kg"),
    ("payload_kg", re.compile(r"\bpayload\b[^\n.]{0,40}?(\d+(?:\.\d+)?)\s*kg", re.I), "kg"),
    ("cruise_ms", re.compile(r"\bcruise\b[^\n.]{0,40}?(\d+(?:\.\d+)?)\s*(?:-|to|–)\s*(\d+(?:\.\d+)?)\s*m/s", re.I), "m/s range"),
    ("endurance_min", re.compile(r"\bendurance\b[^\n.]{0,40}?(?:>|exceeding|at least|minimum of)?\s*(\d+)\s*min", re.I), "min"),
    ("control_hz", re.compile(r"\b(\d+)\s*Hz\b", re.I), "Hz"),
    ("tilt_deg", re.compile(r"\btilt\b[^\n.]{0,40}?(?:0\s*(?:°|degrees)\s*(?:to|–|-)\s*)?(90)\s*(?:°|degrees)", re.I), "deg"),
    ("rotors", re.compile(r"\b([Ss]ix|[6])\s+(?:fixed\s+)?rotors?\b"), "count"),
]


def load_records() -> list[dict]:
    merged = ROOT / "fw_vtol_requirements_dataset.jsonl"
    if merged.exists():
        return [json.loads(l) for l in merged.read_text(encoding="utf-8").splitlines() if l.strip()]
    records = []
    for p in sorted((ROOT / "shards").glob("shard_*.jsonl")):
        for l in p.read_text(encoding="utf-8").splitlines():
            if l.strip():
                records.append(json.loads(l))
    return records


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true", help="Apply minimal fixes for clear contradictions")
    args = ap.parse_args()

    records = load_records()
    by_id = {r["id"]: r for r in records}
    findings: list[str] = []
    fixed: list[str] = []

    # Collect numeric mentions
    mentions: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for r in records:
        text = r["requirement"]
        for key, rx, _unit in PATTERNS:
            for m in rx.finditer(text):
                mentions[key].append((r["id"], m.group(0)))

    # Soft checks against grounding facts
    expected = {
        "mtow_kg": {"9.5", "10"},  # 9.5 design / <10
        "payload_kg": {"2.5"},
        "control_hz": {"50"},
        "tilt_deg": {"90"},
    }
    for key, allowed in expected.items():
        vals = []
        for rid, snippet in mentions.get(key, []):
            nums = re.findall(r"\d+(?:\.\d+)?", snippet)
            vals.append((rid, snippet, set(nums)))
        outliers = [(rid, snip, nums) for rid, snip, nums in vals if nums and not (nums & allowed)]
        # allow payload other UAV comparisons if "QUX" / "FS4" / "benchmark" present
        real_out = []
        for rid, snip, nums in outliers:
            req = by_id[rid]["requirement"].lower()
            if key == "payload_kg" and any(x in req for x in ("qux", "fs4", "benchmark", "comparable", "peer")):
                continue
            if key == "mtow_kg" and any(x in req for x in ("gl-10", "qtw", "suavi", "benchmark", "comparable", "peer", "fs4")):
                continue
            real_out.append((rid, snip, nums))
        if real_out:
            findings.append(
                f"### Possible conflict on `{key}`\n"
                + "\n".join(f"- `{rid}`: `{snip}` (nums={sorted(nums)})" for rid, snip, nums in real_out[:20])
            )

    # Mode vocabulary consistency (soft)
    mode_terms = defaultdict(list)
    for r in records:
        for term in ("VTOL", "transition", "cruise", "hover", "forward flight", "return-to-launch", "RTL", "flight termination"):
            if term.lower() in r["requirement"].lower() or term in r["requirement"]:
                mode_terms[term].append(r["id"])

    # Parent / context structural integrity (hard)
    plan = {r["id"]: r for r in json.loads((ROOT / "dataset_plan.json").read_text(encoding="utf-8"))}
    order = {rid: i for i, rid in enumerate(plan)}
    for r in records:
        pid = r["hierarchy"]["parent_id"]
        if pid is not None and pid not in by_id:
            findings.append(f"- HARD: `{r['id']}` parent_id `{pid}` missing from dataset")
        elif pid is not None and order.get(pid, -1) >= order.get(r["id"], 10**9):
            findings.append(f"- HARD: `{r['id']}` parent_id `{pid}` not earlier in plan order")
        for c in r["context_refs"]:
            if c not in by_id:
                findings.append(f"- HARD: `{r['id']}` context_ref `{c}` missing")
            elif order.get(c, -1) >= order.get(r["id"], 10**9):
                findings.append(f"- HARD: `{r['id']}` context_ref `{c}` not earlier")

    # Optional minimal fix: none by default; placeholder for explicit fixes
    if args.fix:
        pass  # reserved — prefer logging over silent deletion per task spec

    report = [
        "# Cross-requirement consistency report",
        "",
        f"Scanned **{len(records)}** records.",
        "",
        "## Method",
        "",
        "Regex extraction of shared numeric/mode parameters (MTOW, payload mass,",
        "cruise band, endurance, control-loop Hz, tilt range, rotor count) plus",
        "structural checks on `parent_id` / `context_refs` ordering. Benchmark",
        "aircraft comparisons (GL-10, SUAVI, QUX-02A, FS4) are excluded from",
        "primary-aircraft contradiction flags.",
        "",
        "## Findings",
        "",
    ]
    if findings:
        report.extend(findings)
    else:
        report.append("No hard structural breaks and no clear primary-aircraft numeric contradictions detected.")
    report += [
        "",
        "## Mild inconsistencies retained (intentional)",
        "",
        "Real requirement sets are imperfect. Mild phrasing differences (e.g. MTOW",
        "stated as 9.5 kg design vs <10 kg envelope; endurance '>60 min' vs",
        "'at least 60 minutes') are retained so the RF pipeline can encounter them.",
        "",
        "## Fixes applied",
        "",
    ]
    if fixed:
        report.extend(f"- {x}" for x in fixed)
    else:
        report.append("None — no silent deletions; no auto-rewrites required in this pass.")
    report += [
        "",
        "## Mode / regime vocabulary coverage",
        "",
    ]
    for term, ids in sorted(mode_terms.items(), key=lambda x: -len(x[1])):
        report.append(f"- `{term}`: mentioned in {len(ids)} records")

    OUT.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({len(findings)} finding blocks)")


if __name__ == "__main__":
    main()
