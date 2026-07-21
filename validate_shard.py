#!/usr/bin/env python
"""Validate one or more shard JSONL files against dataset_plan.json."""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
plan = {r["id"]: r for r in json.loads((ROOT / "dataset_plan.json").read_text(encoding="utf-8"))}
taxo_ids = set(re.findall(r"- id:\s*(\w+)", (ROOT / "ambiguity_taxonomy.yaml").read_text(encoding="utf-8")))
axis1_ids = {
    "functional", "non_functional_reliability_availability", "non_functional_safety",
    "non_functional_security", "non_functional_usability", "non_functional_maintainability",
    "interface", "constraint",
}
axis2_ids = {
    "structural", "state_driven", "event_driven", "quantitative", "probabilistic",
    "hybrid_continuous", "domain_semantics_heavy",
}


def check(fname: Path, batch_file: Path | None = None) -> int:
    lines = fname.read_text(encoding="utf-8").strip().split("\n")
    seen: set[str] = set()
    problems = 0
    for i, line in enumerate(lines):
        try:
            r = json.loads(line)
        except Exception as e:
            print(f"  line {i}: BAD JSON: {e}")
            problems += 1
            continue
        rid = r.get("id")
        seen.add(rid)
        slot = plan.get(rid)
        if not slot:
            print(f"  {rid}: not in plan!")
            problems += 1
            continue
        if r.get("axis1_nature") != slot["axis1_nature"] or r.get("axis1_nature") not in axis1_ids:
            print(f"  {rid}: axis1 issue got={r.get('axis1_nature')}")
            problems += 1
        if r.get("axis2_behavior") != slot["axis2_behavior"] or r.get("axis2_behavior") not in axis2_ids:
            print(f"  {rid}: axis2 issue got={r.get('axis2_behavior')}")
            problems += 1
        if r.get("hierarchy", {}).get("level") != slot["level"] or r.get("hierarchy", {}).get("parent_id") != slot["parent_id"]:
            print(f"  {rid}: hierarchy mismatch got={r.get('hierarchy')}")
            problems += 1
        if r.get("context_refs") != slot["context_refs"]:
            print(f"  {rid}: context_refs mismatch got={r.get('context_refs')}")
            problems += 1
        amb = r.get("ambiguity", {})
        if amb.get("class") != slot["ambiguity_class"] or amb.get("num_sites") != slot["num_sites"] or len(amb.get("instances", [])) != slot["num_sites"]:
            print(f"  {rid}: ambiguity count/class issue")
            problems += 1
        got = sorted((x["type"], x["family"]) for x in amb.get("instances", []))
        want = sorted((x["type"], x["family"]) for x in slot["ambiguity_sites"])
        if got != want:
            print(f"  {rid}: type/family set mismatch got={got} want={want}")
            problems += 1
        for inst in amb.get("instances", []):
            if inst.get("type") not in taxo_ids:
                print(f"  {rid}: unknown type {inst.get('type')}")
                problems += 1
            if inst.get("trigger") not in r.get("requirement", ""):
                print(f"  {rid}: TRIGGER MISSING {inst.get('trigger')!r}")
                problems += 1
        if len(r.get("nuclear_sentences", [])) != slot["num_obligations"]:
            print(f"  {rid}: nuclear len mismatch got={len(r.get('nuclear_sentences', []))} want={slot['num_obligations']}")
            problems += 1
    missing = set()
    extra = set()
    if batch_file and batch_file.exists():
        plan_ids = {r["id"] for r in json.loads(batch_file.read_text(encoding="utf-8"))["records_to_generate"]}
        missing = plan_ids - seen
        extra = seen - plan_ids
    print(f"{fname.name}: {len(lines)} lines, {problems} problems, missing={missing or set()}, extra={extra or set()}")
    return problems


if __name__ == "__main__":
    args = sys.argv[1:] or [str(p) for p in sorted((ROOT / "shards").glob("shard_*.jsonl"))]
    total = 0
    for a in args:
        p = Path(a)
        batch_name = p.stem.replace("shard_", "")
        batch_file = ROOT / "batches" / f"batch_{batch_name}.json"
        total += check(p, batch_file if batch_file.exists() else None)
    sys.exit(1 if total else 0)
