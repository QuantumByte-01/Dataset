#!/usr/bin/env python
"""Print a few mild cross-requirement inconsistency samples for the summary."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
recs = [
    json.loads(l)
    for l in (ROOT / "fw_vtol_requirements_dataset.jsonl").read_text(encoding="utf-8").splitlines()
    if l.strip()
]
by = {r["id"]: r for r in recs}


def show(rid: str) -> None:
    r = by[rid]
    print(f"--- {rid}")
    print(r["requirement"])
    print()


# Collect candidates
pairs: list[tuple[str, list[str], str]] = []

# 1. Control / telemetry rates
hz_ids = []
for r in recs:
    if re.search(r"\b\d+\s*Hz\b", r["requirement"]):
        hz_ids.append(r["id"])
pairs.append(
    (
        "Loop / reporting rate (50 Hz control vs 10 Hz / 1 Hz monitoring)",
        ["REQ-SYS-012", "REQ-SYS-045", "REQ-SUB-008", "REQ-CMP-027"],
        "Primary FCS loop is specified at 50 Hz, but other requirements also state 10 Hz and 1 Hz rates without saying they are a different channel — a verifier could read them as conflicting control-loop rates.",
    )
)

# 2. Endurance phrasing
pairs.append(
    (
        "Endurance bound phrasing (exceeding vs at least 60 min)",
        ["REQ-ML-002", "REQ-SYS-018"],
        "Mission-level says endurance *exceeding* 60 min; a derived system req says *at least* 60 min. Mild logical tension at the exact 60-minute boundary.",
    )
)

# 3. Safe-state / RTL tension
pairs.append(
    (
        "Safe-state vs geofence/RTL contingency priority",
        ["REQ-SYS-042", "REQ-SYS-043"],
        "One req forces a hard safe-state (zero thrust / hold tilt) on unrecoverable fault; another says the geofence monitor shall *not* command RTL while inside the fence and shall notify GCS when RTL is the 'nearest' contingency — competing recovery policies if a fault occurs inside the fence.",
    )
)

# 4. Link-loss / RTL timing if present
link_ids = [r["id"] for r in recs if re.search(r"link[- ]loss|lost link|datalink loss", r["requirement"], re.I)]
rtl_ids = [r["id"] for r in recs if re.search(r"return-to-launch|\bRTL\b", r["requirement"])]
# pick a couple interesting ones
sample_link = []
for rid in link_ids + rtl_ids:
    t = by[rid]["requirement"].lower()
    if "ms" in t or "second" in t or "s " in t or "timeout" in t or "within" in t:
        sample_link.append(rid)
    if len(sample_link) >= 3:
        break
if len(sample_link) >= 2:
    pairs.append(
        (
            "Link-loss / RTL timing language",
            sample_link[:3],
            "Contingency timing is stated with different numeric windows or vague triggers across datalink vs safety threads.",
        )
    )

# 5. MTOW 9.5 vs <10 if both exist
mtow_ids = [r["id"] for r in recs if re.search(r"9\.5|< ?10|less than 10|under 10", r["requirement"])]
if len(mtow_ids) >= 2:
    pairs.append(
        (
            "Mass envelope (9.5 kg design vs <10 kg)",
            mtow_ids[:3],
            "Design MTOW 9.5 kg vs envelope '<10 kg' appear together across the set — usually compatible, but a strict checker may flag dual ceilings.",
        )
    )

# 6. Find any conflicting payload language
pay = [r["id"] for r in recs if re.search(r"2\.5\s*kg", r["requirement"])]
# look for a looser payload phrasing
loose = [r["id"] for r in recs if re.search(r"payload.*(adequate|sufficient|as needed|approximately)", r["requirement"], re.I)]
if pay and loose:
    pairs.append(
        (
            "Payload mass: hard 2.5 kg vs vague capacity wording",
            (pay[:2] + loose[:2])[:4],
            "Hard 2.5 kg limits coexist with vaguer payload-capacity language elsewhere.",
        )
    )

out_lines = ["# Inconsistency samples (mild — retained on purpose)", ""]
print("=" * 72)
for title, ids, why in pairs:
    print(f"\n## {title}")
    print(why)
    out_lines += [f"## {title}", "", why, ""]
    for rid in ids:
        if rid not in by:
            continue
        show(rid)
        out_lines += [f"**{rid}**", "", f"> {by[rid]['requirement']}", ""]
    out_lines.append("")

# Always dump the strongest concrete Hz + endurance + safe-state samples into the report file
report = ROOT / "inconsistency_samples.md"
report.write_text("\n".join(out_lines), encoding="utf-8")
print(f"\nWrote {report}")
