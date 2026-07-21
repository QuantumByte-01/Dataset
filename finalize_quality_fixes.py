#!/usr/bin/env python
"""Soft quality fixes before final assembly."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def save_jsonl(p: Path, rows: list[dict]) -> None:
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def main() -> None:
    # shard 08: strengthen discourse for REQ-SUB-071
    p08 = ROOT / "shards" / "shard_08_payload.jsonl"
    rows08 = load_jsonl(p08)
    for r in rows08:
        if r["id"] != "REQ-SUB-071":
            continue
        old = "To satisfy the ground-control imagery return obligation,"
        new = "To satisfy the aforementioned ground-control imagery return obligation established above,"
        r["requirement"] = r["requirement"].replace(old, new)
        r["nuclear_sentences"] = [ns.replace(old, new) for ns in r["nuclear_sentences"]]
        for inst in r["ambiguity"]["instances"]:
            assert inst["trigger"] in r["requirement"], inst["trigger"]
        print("fixed", r["id"])
    save_jsonl(p08, rows08)

    # shard 02: strengthen discourse for REQ-CMP-011
    p02 = ROOT / "shards" / "shard_02_propulsion.jsonl"
    rows02 = load_jsonl(p02)
    for r in rows02:
        if r["id"] != "REQ-CMP-011":
            continue
        old = "As part of the thrust distribution described for the propulsion subsystem,"
        new = "As part of the thrust distribution established above for the propulsion subsystem,"
        r["requirement"] = r["requirement"].replace(old, new)
        r["nuclear_sentences"] = [ns.replace(old, new) for ns in r["nuclear_sentences"]]
        for inst in r["ambiguity"]["instances"]:
            assert inst["trigger"] in r["requirement"], inst["trigger"]
        print("fixed", r["id"])
    save_jsonl(p02, rows02)

    # shard 10: expand very short explanations
    expansions = {
        ("REQ-SYS-044", "shortly thereafter"): (
            "'Shortly thereafter' gives no bounded latency for status reporting after "
            "parachute deployment, so readers may treat anything from tens of milliseconds "
            "to several seconds as compliant."
        ),
        ("REQ-SYS-045", "may optionally"): (
            "'May optionally recommend' leaves the flight-termination recommendation "
            "non-mandatory and unverifiable, so an implementation that never recommends "
            "termination still satisfies the wording."
        ),
        ("REQ-SUB-091", "acceptable interval"): (
            "'Acceptable interval' quantifies no maximum elapsed time between fault "
            "declaration and safe-state entry, so competing latency budgets remain compatible "
            "with the text."
        ),
        ("REQ-SUB-091", "sufficiently low"): (
            "'Sufficiently low' rotor thrust gives no numeric thrust bound during the entry "
            "maneuver, leaving hover-capable residual thrust and near-zero thrust as "
            "competing readings."
        ),
        ("REQ-SUB-093", "within 5"): (
            "The value '5' has no unit of measure, so the arming-continuity verification "
            "interval could be 5 ms, 5 s, or another timescale depending on the reader."
        ),
        ("REQ-CMP-086", "may optionally"): (
            "'May optionally ... if needed' makes rotor-thrust authority transfer optional "
            "and leaves the triggering need undefined, so compliance cannot be objectively checked."
        ),
        ("REQ-CMP-089", "promptly"): (
            "'Promptly' gives no bounded detection latency when actuator authority is exceeded "
            "during transition, so sub-cycle and multi-second detections both remain plausible."
        ),
        ("REQ-CMP-093", "tightest feasible"): (
            "'Tightest feasible' clearance margin has no baseline distance or feasibility "
            "criterion, so competing geometric clearances can all be claimed as the tightest "
            "feasible value."
        ),
        ("REQ-CMP-093", "appropriately"): (
            "'Logged appropriately' is subjective and specifies no log format, retention "
            "period, or completeness criterion against which logging quality can be verified."
        ),
    }

    p10 = ROOT / "shards" / "shard_10_safety_flight_termination.jsonl"
    rows10 = load_jsonl(p10)
    nfix = 0
    for r in rows10:
        for inst in r["ambiguity"]["instances"]:
            for (rid, trig), expl in expansions.items():
                if rid == r["id"] and trig == inst["trigger"]:
                    inst["explanation"] = expl
                    nfix += 1
                    break
            else:
                # also allow trigger containment match for short ones
                if len(inst["explanation"].split()) < 12:
                    for (rid, trig), expl in expansions.items():
                        if rid == r["id"] and trig in inst["trigger"]:
                            inst["explanation"] = expl
                            nfix += 1
                            break
    save_jsonl(p10, rows10)
    print("expanded explanations:", nfix)
    print("done")


if __name__ == "__main__":
    main()
