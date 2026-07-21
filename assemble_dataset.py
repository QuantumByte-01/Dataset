#!/usr/bin/env python
"""Merge validated shards into fw_vtol_requirements_dataset.jsonl + dataset_summary.md."""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SHARDS = ROOT / "shards"
OUT_JSONL = ROOT / "fw_vtol_requirements_dataset.jsonl"
OUT_SUMMARY = ROOT / "dataset_summary.md"
MANIFEST = ROOT / "batches" / "_manifest.json"
PLAN = ROOT / "dataset_plan.json"


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    plan = {r["id"]: r for r in json.loads(PLAN.read_text(encoding="utf-8"))}
    records: list[dict] = []
    shard_stats: list[tuple[str, int]] = []

    for m in manifest:
        path = Path(m["output_shard_file"])
        if not path.exists():
            raise SystemExit(f"Missing shard: {path}")
        lines = path.read_text(encoding="utf-8").strip().split("\n")
        if len(lines) != m["n_records"]:
            raise SystemExit(f"{path.name}: expected {m['n_records']} lines, got {len(lines)}")
        for line in lines:
            records.append(json.loads(line))
        shard_stats.append((m["batch_name"], len(lines)))

    # Plan order (ML→SYS→SUB→CMP as built)
    plan_order = [r["id"] for r in json.loads(PLAN.read_text(encoding="utf-8"))]
    by_id = {r["id"]: r for r in records}
    missing = [rid for rid in plan_order if rid not in by_id]
    extra = [rid for rid in by_id if rid not in plan]
    if missing or extra:
        raise SystemExit(f"ID coverage error missing={missing[:10]} extra={extra[:10]}")

    ordered = [by_id[rid] for rid in plan_order]
    with OUT_JSONL.open("w", encoding="utf-8", newline="\n") as f:
        for r in ordered:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    amb = Counter(r["ambiguity"]["class"] for r in ordered)
    levels = Counter(r["hierarchy"]["level"] for r in ordered)
    axis1 = Counter(r["axis1_nature"] for r in ordered)
    axis2 = Counter(r["axis2_behavior"] for r in ordered)
    buckets = Counter(plan[r["id"]]["bucket"] for r in ordered)
    ctx = sum(1 for r in ordered if r["context_refs"])
    sites = Counter(r["ambiguity"]["num_sites"] for r in ordered)
    obls = Counter(len(r["nuclear_sentences"]) for r in ordered)

    lines_out = [
        "# FW-VTOL Requirements Dataset — Summary",
        "",
        f"**Total records:** {len(ordered)}",
        f"**Output:** `{OUT_JSONL.name}`",
        "",
        "## Difficulty buckets (from plan)",
        "",
        f"- precise: {buckets.get('precise', 0)}",
        f"- amb12 (1–2 ambiguity sites emphasis): {buckets.get('amb12', 0)}",
        f"- amb3plus (>2 obligations and/or >2 sites): {buckets.get('amb3plus', 0)}",
        "",
        "## Ambiguity class",
        "",
    ]
    for k in ("precise", "ambiguous", "vague"):
        lines_out.append(f"- {k}: {amb.get(k, 0)}")
    lines_out += ["", "## Hierarchy level", ""]
    for k in ("mission", "system", "subsystem", "component"):
        lines_out.append(f"- {k}: {levels.get(k, 0)}")
    lines_out += ["", "## Axis 1 (nature)", ""]
    for k, v in sorted(axis1.items()):
        lines_out.append(f"- {k}: {v}")
    lines_out += ["", "## Axis 2 (behavior & structure)", ""]
    for k, v in sorted(axis2.items()):
        lines_out.append(f"- {k}: {v}")
    lines_out += [
        "",
        "## Other stats",
        "",
        f"- Records with non-empty `context_refs`: {ctx}",
        f"- `num_sites` distribution: {dict(sorted(sites.items()))}",
        f"- `nuclear_sentences` length distribution: {dict(sorted(obls.items()))}",
        "",
        "## Shards merged",
        "",
    ]
    for name, n in shard_stats:
        lines_out.append(f"- `{name}`: {n} records")
    lines_out += [
        "",
        "## Grounding note",
        "",
        "Primary grounding: METU PhD thesis (tilt-wing/tilt-tail FW-VTOL, 6 rotors,",
        "9.5 kg MTOW, 2.5 kg payload) plus Ducard & Allenspach hybrid VTOL review.",
        "GCS / datalink / FTS threads extend beyond thesis literal text using",
        "`grounding_facts.md` and standard light-UAS practice (e.g. STANAG 4703",
        "payload non-interference, geofence/RTL/FTS contingency patterns) without",
        "contradicting the primary aircraft configuration.",
        "",
        "## Verification / regeneration",
        "",
        "Shard-level automated validation (schema fields vs plan, taxonomy ids,",
        "verbatim triggers, nuclear_sentences counts) was run via `validate_shard.py`.",
        "Any records that failed were regenerated before merge; see individual shard",
        "agent reports and `consistency_report.md` for cross-requirement findings.",
        "",
    ]
    OUT_SUMMARY.write_text("\n".join(lines_out), encoding="utf-8")
    print(f"Wrote {len(ordered)} records -> {OUT_JSONL}")
    print(f"Wrote summary -> {OUT_SUMMARY}")


if __name__ == "__main__":
    main()
