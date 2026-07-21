#!/usr/bin/env python
"""
build_plan.py

Deterministic planning pass for the FW-VTOL requirements dataset.
Allocates all 250 record slots (id, hierarchy level, parent_id, subsystem
thread, difficulty bucket, target ambiguity class + site count + suggested
taxonomy types, context_refs, axis1/axis2 hints) and groups them into
per-subsystem batches with grounding-chunk file assignments, so parallel
generation sub-agents stay consistent with each other.

Outputs:
  dataset_plan.json        - flat list of all 250 planned record slots
  batches/batch_XX_<tag>.json - per-batch slice (plan rows + chunk files
                                 + schema/taxonomy/category file paths)

Run: python build_plan.py
"""
from __future__ import annotations
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHUNK_DIR = ROOT / "extracted_text" / "chunks"
BATCH_DIR = ROOT / "batches"

random.seed(42)

# ---------------------------------------------------------------------
# 1. Subsystem threads (10) — id prefix tags + grounding chunk mapping
# ---------------------------------------------------------------------
SUBSYSTEMS = [
    "airframe_aerostructures",
    "propulsion",
    "tilt_actuation",
    "power_energy",
    "flight_control_system",
    "navigation_sensing",
    "datalink_comms",
    "payload",
    "ground_control_station",
    "safety_flight_termination",
]

DUCARD = "Ducard_Allenspach_ReviewVTOL_Elsevier_Aerospace_Science_and"
CHUNKS = {
    "airframe_aerostructures": [
        "index__05_2_aerodynamic_design_and_optimization.txt",
        "index__01_abstract.txt",
        f"{DUCARD}__03_2_platform_designs.txt",
    ],
    "propulsion": [
        "index__03_4_rotors.txt",
        "index__08_0_rpm.txt",
        "index__05_2_aerodynamic_design_and_optimization.txt",
    ],
    "tilt_actuation": [
        "index__08_0_rpm.txt",
        "index__06_3_nonlinear_dynamic_model.txt",
        f"{DUCARD}__08_2_2_2_tiltrotor_aircraft.txt",
        f"{DUCARD}__09_2_2_3_tiltwing_aircraft.txt",
    ],
    "power_energy": [
        "index__05_2_aerodynamic_design_and_optimization.txt",
        "index__01_abstract.txt",
    ],
    "flight_control_system": [
        "index__10_5_controller_design.txt",
        "index__09_4_linear_analysis.txt",
        f"{DUCARD}__21_5_control_of_unmanned_hybrid_convertible.txt",
        f"{DUCARD}__27_5_2_uni_ed_control_approaches.txt",
        f"{DUCARD}__22_5_1_scheduled_control_approaches.txt",
    ],
    "navigation_sensing": [
        "index__06_3_nonlinear_dynamic_model.txt",
        "index__09_4_linear_analysis.txt",
        f"{DUCARD}__11_3_1_common_6_degree_of_freedom_dof_trans.txt",
    ],
    "datalink_comms": [
        "index__02_1_introduction.txt",
        f"{DUCARD}__01_1_introduction.txt",
    ],
    "payload": [
        "index__02_1_introduction.txt",
        "index__05_2_aerodynamic_design_and_optimization.txt",
    ],
    "ground_control_station": [
        "index__02_1_introduction.txt",
        "index__11_6_simulation_results.txt",
    ],
    "safety_flight_termination": [
        f"{DUCARD}__32_6_control_allocation.txt",
        "index__11_6_simulation_results.txt",
        f"{DUCARD}__43_7_conclusion.txt",
    ],
}
INTEGRATION_CHUNKS = [
    "index__01_abstract.txt",
    "index__02_1_introduction.txt",
    f"{DUCARD}__01_1_introduction.txt",
    f"{DUCARD}__02_1_authors_contributed_equally_to_the_wor.txt",
]

# ---------------------------------------------------------------------
# 2. Axis rotation pools (from requirement_categories.yaml)
# ---------------------------------------------------------------------
AXIS1 = ["functional", "non_functional_reliability_availability", "non_functional_safety",
         "non_functional_security", "non_functional_usability",
         "non_functional_maintainability", "interface", "constraint"]
AXIS2 = ["structural", "state_driven", "event_driven", "quantitative",
         "probabilistic", "hybrid_continuous", "domain_semantics_heavy"]

# subsystem -> axis1/axis2 weighting (which categories are plausible there)
AXIS_BIAS = {
    "airframe_aerostructures": (["constraint", "functional", "non_functional_maintainability"],
                                 ["structural", "quantitative"]),
    "propulsion": (["functional", "constraint", "non_functional_reliability_availability"],
                   ["quantitative", "state_driven", "hybrid_continuous"]),
    "tilt_actuation": (["functional", "interface"],
                        ["state_driven", "event_driven", "hybrid_continuous"]),
    "power_energy": (["non_functional_reliability_availability", "constraint", "functional"],
                      ["quantitative", "event_driven", "probabilistic"]),
    "flight_control_system": (["functional", "non_functional_safety"],
                               ["hybrid_continuous", "state_driven", "domain_semantics_heavy"]),
    "navigation_sensing": (["functional", "interface", "non_functional_reliability_availability"],
                            ["quantitative", "probabilistic", "event_driven"]),
    "datalink_comms": (["interface", "non_functional_security"],
                        ["event_driven", "quantitative", "state_driven"]),
    "payload": (["functional", "interface", "constraint"],
                ["structural", "quantitative", "event_driven"]),
    "ground_control_station": (["non_functional_usability", "functional", "interface"],
                                ["event_driven", "state_driven", "domain_semantics_heavy"]),
    "safety_flight_termination": (["non_functional_safety", "non_functional_reliability_availability"],
                                   ["event_driven", "state_driven", "probabilistic"]),
}

# ---------------------------------------------------------------------
# 3. Taxonomy type pools (mirrors ambiguity_taxonomy.yaml ids)
# ---------------------------------------------------------------------
TRUE_AMBIGUITY_TYPES = [
    ("coordination", "syntactic_structural"),
    ("pp_attachment", "syntactic_structural"),
    ("sequence_syntactic", "syntactic_structural"),
    ("homonymy", "lexical"),
    ("polysemy", "lexical"),
    ("coreferential", "referential"),
    ("underspecification_common_noun", "referential"),
    ("metonymy", "referential"),
    ("elliptical", "referential"),
    ("scope_quantification", "scopal"),
    ("scope_negation", "scopal"),
    ("scope_numbers", "scopal"),
    ("presuppositional", "pragmatic"),
    ("idiomatic", "pragmatic"),
    ("generic_nongeneric", "pragmatic"),
    ("type_ambiguity", "pragmatic"),
]
VAGUE_TYPES = [
    ("temporal_vagueness", "vagueness"),
    ("threshold_vagueness", "vagueness"),
    ("comparative_superlative", "vagueness"),
    ("subject_vagueness", "vagueness"),
    ("subjectivity", "vagueness"),
    ("optionality_vague_modals", "vagueness"),
    ("underspecification", "incompleteness"),
    ("missing_units", "incompleteness"),
]

_true_cycle = TRUE_AMBIGUITY_TYPES * 6
_vague_cycle = VAGUE_TYPES * 6
random.shuffle(_true_cycle)
random.shuffle(_vague_cycle)
_true_iter = iter(_true_cycle)
_vague_iter = iter(_vague_cycle)


def next_true():
    global _true_iter
    try:
        return next(_true_iter)
    except StopIteration:
        random.shuffle(_true_cycle)
        _true_iter = iter(_true_cycle)
        return next(_true_iter)


def next_vague():
    global _vague_iter
    try:
        return next(_vague_iter)
    except StopIteration:
        random.shuffle(_vague_cycle)
        _vague_iter = iter(_vague_cycle)
        return next(_vague_iter)


def make_sites(bucket: str):
    """Return (class, list[(type,family)]) for a record given its difficulty bucket."""
    if bucket == "precise":
        return "precise", []

    if bucket == "amb12":
        n = random.choice([1, 1, 2, 2, 2])
        is_vague = random.random() < 0.4
        if is_vague:
            sites = [next_vague() for _ in range(n)]
            return "vague", sites
        sites = [next_true()]
        for _ in range(n - 1):
            sites.append(next_vague() if random.random() < 0.35 else next_true())
        return "ambiguous", sites

    # amb3plus
    high_sites = random.random() < 0.7
    if high_sites:
        n = random.choice([3, 3, 4, 5])
        is_vague = random.random() < 0.3
        if is_vague:
            sites = [next_vague() for _ in range(n)]
            return "vague", sites
        sites = [next_true()]
        for _ in range(n - 1):
            sites.append(next_vague() if random.random() < 0.4 else next_true())
        return "ambiguous", sites
    else:
        # bundling-heavy: fewer sites but >2 obligations enforced by caller
        n = random.choice([1, 2])
        is_vague = random.random() < 0.4
        if is_vague:
            sites = [next_vague() for _ in range(n)]
            return "vague", sites
        sites = [next_true()]
        for _ in range(n - 1):
            sites.append(next_vague() if random.random() < 0.35 else next_true())
        return "ambiguous", sites


def make_obligations(bucket: str, high_sites: bool | None):
    if bucket == "precise":
        return 1
    if bucket == "amb12":
        return random.choice([1, 1, 1, 2, 2, 3])
    # amb3plus
    if high_sites:
        return random.choice([1, 2, 2, 3, 4])
    return random.choice([3, 4, 5])


# ---------------------------------------------------------------------
# 4. Build the 250 slots: ML(10) SYS(45) SUB(100) CMP(95)
# ---------------------------------------------------------------------
plan = []
id_counters = {"ML": 0, "SYS": 0, "SUB": 0, "CMP": 0}
introduced = {}  # subsystem_tag -> list of ids introduced so far (in order)
for tag in SUBSYSTEMS:
    introduced[tag] = []
introduced["_integration"] = []

def new_id(prefix):
    id_counters[prefix] += 1
    return f"REQ-{prefix}-{id_counters[prefix]:03d}"

# ---- Mission level (10) ----
mission_topics = [
    "overall FW-VTOL mission capability (VTOL + cruise + payload delivery)",
    "operational endurance and range envelope",
    "payload carriage capability",
    "autonomous mission execution and waypoint navigation",
    "operator command and monitoring capability",
    "environmental operating envelope for the mission",
    "safety-of-flight and contingency-return capability",
    "airworthiness / regulatory compliance posture",
    "transportability and field deployability",
    "data/imagery return-to-operator capability",
]
mission_ids = []
for i, topic in enumerate(mission_topics):
    rid = new_id("ML")
    mission_ids.append(rid)
    introduced["_integration"].append(rid)
    plan.append({
        "id": rid, "level": "mission", "parent_id": None,
        "subsystem_tag": "_integration", "topic_hint": topic,
        "bucket": None,  # filled later
    })

# ---- System level (45): 5 integration + 4 per subsystem (40) ----
sys_integration_topics = [
    "cross-subsystem mode transition (vertical <-> forward flight) coordination",
    "system-level health monitoring and fault reporting",
    "system-level interface control between airframe, propulsion and FCS",
    "system-level mass/power budget allocation across subsystems",
    "system-level compliance with a named airworthiness standard",
]
for i, topic in enumerate(sys_integration_topics):
    rid = new_id("SYS")
    introduced["_integration"].append(rid)
    plan.append({
        "id": rid, "level": "system", "parent_id": mission_ids[i % len(mission_ids)],
        "subsystem_tag": "_integration", "topic_hint": topic, "bucket": None,
    })

sys_topics_by_subsystem = {
    "airframe_aerostructures": ["wing/tail structural load capability", "mass budget compliance",
                                 "aerodynamic performance across flight regimes", "structural interface to propulsion/tilt mounts"],
    "propulsion": ["thrust-to-weight capability across the envelope", "rotor redundancy on partial failure",
                   "propulsion system interface to FCS", "propulsion thermal/power limits"],
    "tilt_actuation": ["wing/tail tilt range and rate capability", "tilt subsystem interface to FCS",
                        "tilt actuator fault behavior", "tilt position sensing accuracy"],
    "power_energy": ["energy budget for full mission profile", "power distribution to subsystems",
                      "battery health monitoring", "power subsystem interface to propulsion and payload"],
    "flight_control_system": ["6-DoF control across all trim points", "gain-scheduled control through transition",
                               "control allocation across rotors and surfaces", "FCS interface to navigation and actuators"],
    "navigation_sensing": ["state estimation accuracy across flight regimes", "sensor suite redundancy",
                            "navigation interface to FCS", "sensor fault detection"],
    "datalink_comms": ["command and telemetry link availability", "link interface to GCS",
                        "link security posture", "link loss contingency behavior"],
    "payload": ["payload capacity and mounting interface", "payload power/data interface",
                "payload effect on flight envelope", "payload data return to GCS"],
    "ground_control_station": ["GCS mission planning and monitoring capability", "GCS-to-aircraft command interface",
                                "GCS operator alerting", "GCS logging of flight data"],
    "safety_flight_termination": ["system-level safe-state definition", "geofence and RTL capability",
                                   "flight termination interface", "safety monitoring across subsystems"],
}
for tag in SUBSYSTEMS:
    for topic in sys_topics_by_subsystem[tag]:
        rid = new_id("SYS")
        introduced[tag].append(rid)
        # parent: an integration ML/SYS id that matches thematically, fallback round robin
        parent = mission_ids[hash((tag, topic)) % len(mission_ids)]
        plan.append({
            "id": rid, "level": "system", "parent_id": parent,
            "subsystem_tag": tag, "topic_hint": topic, "bucket": None,
        })

# ---- Subsystem level (100): 10 per subsystem ----
sub_topic_templates = [
    "primary functional obligation of {sub}",
    "{sub} performance envelope / quantitative bound",
    "{sub} interface to an adjacent subsystem",
    "{sub} behavior in a specific flight mode/state",
    "{sub} response to a triggering event",
    "{sub} fault/degraded-mode behavior",
    "{sub} design constraint (mass/volume/standard)",
    "{sub} monitoring/reporting obligation",
    "{sub} calibration/initialization obligation",
    "{sub} redundancy or margin requirement",
]
for tag in SUBSYSTEMS:
    sys_ids_here = [p["id"] for p in plan if p["level"] == "system" and p["subsystem_tag"] == tag]
    for i, tmpl in enumerate(sub_topic_templates):
        rid = new_id("SUB")
        introduced[tag].append(rid)
        parent = sys_ids_here[i % len(sys_ids_here)]
        plan.append({
            "id": rid, "level": "subsystem", "parent_id": parent,
            "subsystem_tag": tag, "topic_hint": tmpl.format(sub=tag.replace("_", " ")),
            "bucket": None,
        })

# ---- Component level (95): uneven split summing to 95 ----
cmp_counts = {"airframe_aerostructures": 9, "propulsion": 9, "tilt_actuation": 9, "power_energy": 9,
              "flight_control_system": 9, "navigation_sensing": 10, "datalink_comms": 10, "payload": 10,
              "ground_control_station": 10, "safety_flight_termination": 10}
assert sum(cmp_counts.values()) == 95
cmp_topic_templates = [
    "a named component's precise obligation within {sub}",
    "a named component's quantitative parameter within {sub}",
    "a named component's interface to its parent subsystem",
    "a named component's event-triggered response within {sub}",
    "a named component's fault-condition response within {sub}",
    "a named component's state/mode-dependent behavior within {sub}",
    "a named component's design constraint within {sub}",
    "a named component's calibration/init obligation within {sub}",
    "a named component's monitoring/telemetry obligation within {sub}",
    "a named component's margin/tolerance requirement within {sub}",
]
for tag in SUBSYSTEMS:
    sub_ids_here = [p["id"] for p in plan if p["level"] == "subsystem" and p["subsystem_tag"] == tag]
    n = cmp_counts[tag]
    for i in range(n):
        rid = new_id("CMP")
        introduced[tag].append(rid)
        parent = sub_ids_here[i % len(sub_ids_here)]
        tmpl = cmp_topic_templates[i % len(cmp_topic_templates)]
        plan.append({
            "id": rid, "level": "component", "parent_id": parent,
            "subsystem_tag": tag, "topic_hint": tmpl.format(sub=tag.replace("_", " ")),
            "bucket": None,
        })

assert len(plan) == 250, len(plan)

# ---------------------------------------------------------------------
# 5. Assign difficulty buckets: 50 precise / 100 amb12 / 100 amb3plus
#    Shuffle assignment order (not record order) so buckets interleave
#    across levels/subsystems.
# ---------------------------------------------------------------------
bucket_pool = ["precise"] * 50 + ["amb12"] * 100 + ["amb3plus"] * 100
random.shuffle(bucket_pool)
# never let mission-level be amb3plus-bundling >90% precise-ish; just assign directly,
# shuffle already guarantees spread since plan order interleaves ML/SYS/SUB/CMP per subsystem.
order = list(range(len(plan)))
random.shuffle(order)
for idx, bucket in zip(order, bucket_pool):
    plan[idx]["bucket"] = bucket

# ---------------------------------------------------------------------
# 6. Assign ambiguity class / sites / obligation counts + axis1/axis2
# ---------------------------------------------------------------------
for rec in plan:
    bucket = rec["bucket"]
    if bucket == "amb3plus":
        high = random.random() < 0.7
        rec["_high_sites"] = high
    else:
        rec["_high_sites"] = None
    amb_class, sites = make_sites(bucket)
    rec["ambiguity_class"] = amb_class
    rec["ambiguity_sites"] = [{"type": t, "family": f} for t, f in sites]
    rec["num_sites"] = len(sites)
    rec["num_obligations"] = make_obligations(bucket, rec["_high_sites"])

    tag = rec["subsystem_tag"]
    if tag == "_integration":
        a1_pool, a2_pool = AXIS1, AXIS2
    else:
        a1_pool, a2_pool = AXIS_BIAS[tag]
    rec["axis1_nature"] = random.choice(a1_pool)
    rec["axis2_behavior"] = random.choice(a2_pool)
    rec.pop("_high_sites", None)

# ---------------------------------------------------------------------
# 7. context_refs: ~15% of non-mission records get 1 back-reference
#    within the same subsystem thread (or _integration), to an id
#    introduced earlier (excluding its own direct parent).
# ---------------------------------------------------------------------
by_id = {r["id"]: r for r in plan}
non_mission = [r for r in plan if r["level"] != "mission"]
random.shuffle(non_mission)
n_context = max(1, int(len(non_mission) * 0.16))
context_targets = non_mission[:n_context]
context_target_ids = {r["id"] for r in context_targets}

for r in plan:
    r["context_refs"] = []

# process in generation order so "earlier" is well-defined (ML->SYS->SUB->CMP, id order)
ordered_ids = [r["id"] for r in plan]
pos = {rid: i for i, rid in enumerate(ordered_ids)}
for r in plan:
    if r["id"] not in context_target_ids:
        continue
    tag = r["subsystem_tag"]
    pool = [rid for rid in introduced.get(tag, []) if pos[rid] < pos[r["id"]] and rid != r["parent_id"]]
    if not pool:
        continue
    r["context_refs"] = [random.choice(pool)]

# ---------------------------------------------------------------------
# 8. Write dataset_plan.json
# ---------------------------------------------------------------------
ROOT_OUT = ROOT / "dataset_plan.json"
ROOT_OUT.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")

# ---------------------------------------------------------------------
# 9. Build per-subsystem batches (+ 1 integration batch) for parallel gen
# ---------------------------------------------------------------------
BATCH_DIR.mkdir(exist_ok=True)
batches = []
integration_rows = [r for r in plan if r["subsystem_tag"] == "_integration"]
batches.append(("00_integration", "_integration", integration_rows, INTEGRATION_CHUNKS))
for i, tag in enumerate(SUBSYSTEMS, start=1):
    rows = [r for r in plan if r["subsystem_tag"] == tag]
    batches.append((f"{i:02d}_{tag}", tag, rows, CHUNKS[tag]))

manifest = []
for name, tag, rows, chunk_files in batches:
    batch_obj = {
        "batch_name": name,
        "subsystem_tag": tag,
        "grounding_chunk_files": [str((CHUNK_DIR / f)) for f in chunk_files],
        "shared_config_files": {
            "schema_and_contract": str(ROOT / "dataset_schema.md"),
            "ambiguity_taxonomy": str(ROOT / "ambiguity_taxonomy.yaml"),
            "requirement_categories": str(ROOT / "requirement_categories.yaml"),
            "grounding_facts": str(ROOT / "grounding_facts.md"),
        },
        "output_shard_file": str(ROOT / "shards" / f"shard_{name}.jsonl"),
        "records_to_generate": rows,
    }
    out_path = BATCH_DIR / f"batch_{name}.json"
    out_path.write_text(json.dumps(batch_obj, indent=2, ensure_ascii=False), encoding="utf-8")
    manifest.append({"batch_name": name, "subsystem_tag": tag, "n_records": len(rows),
                      "batch_file": str(out_path), "output_shard_file": batch_obj["output_shard_file"]})

(BATCH_DIR / "_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
(ROOT / "shards").mkdir(exist_ok=True)

# ---------------------------------------------------------------------
# 10. Report
# ---------------------------------------------------------------------
from collections import Counter
print("Levels:", Counter(r["level"] for r in plan))
print("Buckets:", Counter(r["bucket"] for r in plan))
print("Ambiguity class:", Counter(r["ambiguity_class"] for r in plan))
print("context_refs count:", sum(1 for r in plan if r["context_refs"]))
print("Batches:")
for m in manifest:
    print(f"  {m['batch_name']:28s} n={m['n_records']:3d}  -> {m['batch_file']}")
