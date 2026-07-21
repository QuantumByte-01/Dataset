#!/usr/bin/env python
"""Deep quality audit comparing early vs late shards and full merged dataset."""
from __future__ import annotations

import json
import re
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def parse_family_map(taxo_text: str) -> dict[str, str]:
    family_of: dict[str, str] = {}
    cur_family = None
    in_families = False
    for line in taxo_text.splitlines():
        if line.startswith("families:"):
            in_families = True
            continue
        if not in_families:
            continue
        fm = re.match(r"^  ([a-z_]+):\s*$", line)
        if fm:
            cur_family = fm.group(1)
            continue
        tm = re.match(r"^\s+- id:\s*(\w+)", line)
        if tm and cur_family:
            family_of[tm.group(1)] = cur_family
    return family_of


def shard_metrics(rows: list[dict]) -> dict:
    wl = [len(r["requirement"].split()) for r in rows]
    expl = [len(inst["explanation"].split()) for r in rows for inst in r["ambiguity"]["instances"]]
    return {
        "n": len(rows),
        "med_words": int(statistics.median(wl)) if wl else 0,
        "mean_words": round(statistics.mean(wl), 1) if wl else 0,
        "med_expl": int(statistics.median(expl)) if expl else 0,
        "shall_pct": round(100 * sum(1 for r in rows if "shall" in r["requirement"].lower()) / len(rows), 1),
        "multi_sent": sum(1 for r in rows if r["requirement"].count(".") >= 2),
    }


def main() -> None:
    plan = {r["id"]: r for r in json.loads((ROOT / "dataset_plan.json").read_text(encoding="utf-8"))}
    taxo = (ROOT / "ambiguity_taxonomy.yaml").read_text(encoding="utf-8")
    taxo_ids = set(re.findall(r"- id:\s*(\w+)", taxo))
    family_of = parse_family_map(taxo)

    recs = [
        json.loads(l)
        for l in (ROOT / "fw_vtol_requirements_dataset.jsonl").read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]
    by_shard = {
        p.stem: [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
        for p in sorted((ROOT / "shards").glob("shard_*.jsonl"))
    }

    print("=== TOTAL", len(recs))
    problems: list[tuple[str, str]] = []
    true_fams = {"syntactic_structural", "lexical", "referential", "scopal", "pragmatic"}

    for r in recs:
        s = plan[r["id"]]
        if r["axis1_nature"] != s["axis1_nature"] or r["axis2_behavior"] != s["axis2_behavior"]:
            problems.append((r["id"], "axis mismatch"))
        if r["hierarchy"]["level"] != s["level"] or r["hierarchy"]["parent_id"] != s["parent_id"]:
            problems.append((r["id"], "hierarchy mismatch"))
        if r["context_refs"] != s["context_refs"]:
            problems.append((r["id"], "context_refs mismatch"))
        amb = r["ambiguity"]
        if (
            amb["class"] != s["ambiguity_class"]
            or amb["num_sites"] != s["num_sites"]
            or len(amb["instances"]) != s["num_sites"]
        ):
            problems.append((r["id"], "amb count/class"))
        got = sorted((x["type"], x["family"]) for x in amb["instances"])
        want = sorted((x["type"], x["family"]) for x in s["ambiguity_sites"])
        if got != want:
            problems.append((r["id"], f"type/family {got}!={want}"))
        for inst in amb["instances"]:
            if inst["type"] not in taxo_ids:
                problems.append((r["id"], f"bad type {inst['type']}"))
            if family_of.get(inst["type"]) and inst["family"] != family_of[inst["type"]]:
                problems.append(
                    (r["id"], f"family wrong for {inst['type']}: {inst['family']} vs {family_of[inst['type']]}")
                )
            if inst["trigger"] not in r["requirement"]:
                problems.append((r["id"], f"trigger missing {inst['trigger']!r}"))
            if not inst.get("explanation") or len(inst["explanation"]) < 20:
                problems.append((r["id"], "thin explanation"))
        if len(r["nuclear_sentences"]) != s["num_obligations"]:
            problems.append((r["id"], "nuclear len"))
        fams = {x["family"] for x in amb["instances"]}
        if amb["class"] == "precise" and amb["instances"]:
            problems.append((r["id"], "precise with instances"))
        if amb["class"] == "vague" and fams & true_fams:
            problems.append((r["id"], "vague but has true-ambiguity family"))
        if amb["class"] == "ambiguous" and amb["instances"] and not (fams & true_fams):
            problems.append((r["id"], "ambiguous without true-ambiguity family"))

    print("Hard problems:", len(problems))
    for p in problems[:40]:
        print(" ", p)

    empty_req = [r["id"] for r in recs if len(r["requirement"].split()) < 8]
    topic_leak = [
        r["id"]
        for r in recs
        if "topic_hint" in r["requirement"] or "a named component" in r["requirement"].lower()
    ]
    dup_req = [k for k, v in Counter(r["requirement"] for r in recs).items() if v > 1]
    shall_count = sum(1 for r in recs if "shall" in r["requirement"].lower())
    word_lens = [len(r["requirement"].split()) for r in recs]
    print("\n=== QUALITY HEURISTICS")
    print("short reqs (<8 words):", empty_req)
    print("topic_hint leaks:", topic_leak)
    print("duplicate requirement texts:", len(dup_req))
    print("shall coverage:", shall_count, "/", len(recs))
    print("word len: min/med/max", min(word_lens), int(statistics.median(word_lens)), max(word_lens))

    precise_drift = []
    for r in recs:
        if r["ambiguity"]["class"] != "precise":
            continue
        req = r["requirement"].strip().rstrip(".")
        nuc = r["nuclear_sentences"][0].strip().rstrip(".")
        if req.lower() != nuc.lower() and abs(len(req) - len(nuc)) > 40:
            precise_drift.append((r["id"], abs(len(req) - len(nuc))))
    print("precise with large nuclear drift (>40 chars):", len(precise_drift))
    for x in precise_drift[:8]:
        print(" ", x)

    trig = Counter()
    for r in recs:
        for inst in r["ambiguity"]["instances"]:
            trig[inst["trigger"].lower()] += 1
    print("top repeated triggers:")
    for t, c in trig.most_common(15):
        print(f"  {c:3d}  {t!r}")

    types = Counter(inst["type"] for r in recs for inst in r["ambiguity"]["instances"])
    print("taxonomy type coverage:", len(types), "of", len(taxo_ids))
    print("unused taxonomy types:", sorted(taxo_ids - set(types)))

    ground_hits = Counter()
    keys = [
        "tilt",
        "rotor",
        "9.5",
        "2.5",
        "50 Hz",
        "15",
        "25",
        "m/s",
        "VTOL",
        "transition",
        "LiPo",
        "6-DoF",
        "gain schedul",
    ]
    for r in recs:
        text = r["requirement"]
        for k in keys:
            if k.lower() in text.lower() or k in text:
                ground_hits[k] += 1
    print("grounding keyword hits:", dict(ground_hits))

    weak_ctx = []
    for r in recs:
        if not r["context_refs"]:
            continue
        t = r["requirement"].lower()
        cues = [
            "aforementioned",
            "above",
            "that ",
            "those ",
            "this ",
            "these ",
            "it ",
            "they ",
            "the latter",
            "as defined",
            "established",
            "previously",
            "such ",
            "prior",
            "earlier",
            "same ",
        ]
        if not any(c in t for c in cues):
            weak_ctx.append(r["id"])
    print("context_refs with weak discourse cues:", len(weak_ctx), weak_ctx[:20])

    print("\n=== EARLY vs LATE SHARD METRICS")
    for name in sorted(by_shard):
        m = shard_metrics(by_shard[name])
        print(
            f"{name:40s} n={m['n']:3d} med_w={m['med_words']:3d} "
            f"mean_w={m['mean_words']:5.1f} shall%={m['shall_pct']:5.1f} "
            f"multi_sent={m['multi_sent']:2d} med_expl={m['med_expl']}"
        )

    short_nuc = []
    for r in recs:
        for i, n in enumerate(r["nuclear_sentences"]):
            if len(n.split()) < 5:
                short_nuc.append((r["id"], i, n))
    print("\nshort nuclear sentences:", len(short_nuc))
    for x in short_nuc[:10]:
        print(" ", x)

    order = {rid: i for i, rid in enumerate(plan)}
    bad_parent = []
    bad_ctx = []
    for r in recs:
        pid = r["hierarchy"]["parent_id"]
        if pid is not None and (pid not in plan or order[pid] >= order[r["id"]]):
            bad_parent.append(r["id"])
        for c in r["context_refs"]:
            if c not in plan or order[c] >= order[r["id"]]:
                bad_ctx.append(r["id"])
    print("bad parent/ctx order:", bad_parent, bad_ctx)

    expected_keys = {
        "id",
        "requirement",
        "axis1_nature",
        "axis2_behavior",
        "hierarchy",
        "context_refs",
        "ambiguity",
        "nuclear_sentences",
    }
    key_issues = [r["id"] for r in recs if set(r.keys()) != expected_keys]
    print("unexpected field sets count:", len(key_issues), key_issues[:10])

    # Spot-check: sample 3 late-shard amb3plus vs 3 early
    print("\n=== SPOT CHECK LATE amb3plus (first of each late shard)")
    for sn in ("shard_08_payload", "shard_09_ground_control_station", "shard_10_safety_flight_termination"):
        for r in by_shard[sn]:
            if plan[r["id"]]["bucket"] == "amb3plus":
                print("---", r["id"], "sites", r["ambiguity"]["num_sites"], "obl", len(r["nuclear_sentences"]))
                print(r["requirement"][:280])
                print("triggers:", [i["trigger"] for i in r["ambiguity"]["instances"]])
                break

    print("\n=== SPOT CHECK EARLY amb3plus")
    for sn in ("shard_00_integration", "shard_01_airframe_aerostructures", "shard_02_propulsion"):
        for r in by_shard[sn]:
            if plan[r["id"]]["bucket"] == "amb3plus":
                print("---", r["id"], "sites", r["ambiguity"]["num_sites"], "obl", len(r["nuclear_sentences"]))
                print(r["requirement"][:280])
                print("triggers:", [i["trigger"] for i in r["ambiguity"]["instances"]])
                break


if __name__ == "__main__":
    main()
