#!/usr/bin/env python
import json

recs = [json.loads(l) for l in open("fw_vtol_requirements_dataset.jsonl", encoding="utf-8")]
by_id = {r["id"]: r for r in recs}

# 1. REQ-ML-004: insert missing "and" before "shall not deviate"
r = by_id["REQ-ML-004"]
r["requirement"] = r["requirement"].replace(
    "to the ground control station, shall not deviate",
    "to the ground control station, and shall not deviate"
)

# 2. REQ-ML-008: insert missing "and" before "shall maintain"
r = by_id["REQ-ML-008"]
r["requirement"] = r["requirement"].replace(
    "for fixed-wing light UAS, shall maintain",
    "for fixed-wing light UAS, and shall maintain"
)

# 3. REQ-SYS-035: gold-defect merge (compound object, tool would not split it) - trim 4->3
r = by_id["REQ-SYS-035"]
r["nuclear_sentences"] = [
    "The payload subsystem shall hand over 28 V DC power and the serial data bus to the EO/IR gimbal camera through the payload power/data harness.",
    "The payload subsystem shall isolate the payload interface controller from airframe EMI.",
    "The payload subsystem shall maintain return-path continuity to the same standard as the datalink subsystem."
]

# 4. REQ-SUB-043: rewrite bare infinitival list into repeated explicit "shall" clauses
r = by_id["REQ-SUB-043"]
r["requirement"] = ("The flight control system shall send tilt-angle commands to the tilt-actuation subsystem, "
                     "and shall receive tilt-angle feedback from the tilt-actuation subsystem, "
                     "and shall synchronize gain-schedule updates across both tilt actuators.")

# 5. REQ-SUB-048: rewrite passive compound-subject list into 3 repeated determiner+noun+"shall be reported" clauses
r = by_id["REQ-SUB-048"]
r["requirement"] = ("While airborne, the flight control system shall continuously monitor its own control-loop health, "
                     "and when tracking error becomes high, the trim-point tracking error shall be reported to the ground control station, "
                     "and the gain-schedule transition status shall be reported to the ground control station, "
                     "and the control-allocator saturation shall be reported to the ground control station.")
for inst in r["ambiguity"]["instances"]:
    if inst["trigger"] == "shall each be reported":
        inst["trigger"] = "shall be reported"
        inst["explanation"] = ("the passive construction \"shall be reported\" does not name which component - "
                                "the flight control system itself, the datalink subsystem, or a logging service - "
                                "performs the reporting, and this omission repeats across all three reported parameters.")
r["nuclear_sentences"] = [
    "While airborne, the flight control system shall continuously monitor its own control-loop health.",
    "When tracking error becomes high, the trim-point tracking error shall be reported to the ground control station.",
    "When tracking error becomes high, the gain-schedule transition status shall be reported to the ground control station.",
    "When tracking error becomes high, the control-allocator saturation shall be reported to the ground control station."
]

# 6. REQ-SUB-065: insert missing "and" before "it shall re-synchronize"
r = by_id["REQ-SUB-065"]
r["requirement"] = r["requirement"].replace(
    "to the ground control station, it shall re-synchronize",
    "to the ground control station, and it shall re-synchronize"
)

# 7. REQ-SUB-073: gold-defect merge (redundant re-decomposition of one clause) - trim 3->2
r = by_id["REQ-SUB-073"]
r["nuclear_sentences"] = [
    "The payload interface controller may periodically exchange health status with the flight control system over the serial data bus at a rate of 10.",
    "Following payload bay door closure, the payload interface controller shall synchronize gimbal pointing to the navigation solution once practicable using parameters as specified elsewhere."
]

# 8. REQ-SUB-074: genuine Oxford-comma VP-list, insert "and shall" before each subsequent verb
r = by_id["REQ-SUB-074"]
r["requirement"] = ("When the air vehicle enters FORWARD_FLIGHT at true airspeed above 15 m/s, the payload subsystem shall enable the EO/IR gimbal camera, "
                     "and shall stabilize the gimbal stabilization unit, "
                     "and shall begin recording on all onboard storage devices, "
                     "and shall report payload-ready status to the flight control system.")

# 9. REQ-SUB-079: gold-defect trim (atomics 3+4 are artificial re-decomposition of atomic 2) - trim 4->2
r = by_id["REQ-SUB-079"]
r["nuclear_sentences"] = [
    "Before the EO/IR gimbal camera resumes stabilized imaging after power cycling, the payload subsystem shall not release the payload bay latch without confirming gimbal initialization on the payload interface controller.",
    "Before the EO/IR gimbal camera resumes stabilized imaging after power cycling, the ground station shall again verify boresight alignment to the highest accuracy achievable with the fuselage payload bay door open using the calibration target."
]

# 10. REQ-CMP-067: 5-way Oxford-comma VP-list, insert "and shall" before each subsequent verb
r = by_id["REQ-CMP-067"]
r["requirement"] = ("The payload bay latch shall engage within 500 ms of door closure command, "
                     "and shall maintain hold force above 150 during vibration testing, "
                     "and shall release when unlock voltage exceeds 12, "
                     "and shall begin re-latch monitoring shortly after payload swap, "
                     "and shall provide the lowest possible mechanical backlash in the secured state.")

# 11. REQ-CMP-069: 4-way Oxford-comma VP-list with leading trigger, insert "and shall"
r = by_id["REQ-CMP-069"]
r["requirement"] = ("When commanded to a new track point, the gimbal stabilization unit shall slew to within 2 degrees of the target line-of-sight within 800, "
                     "and shall hold that orientation with minimal drift during cruise at 15-25 m/s, "
                     "and shall report slew-complete when angular error falls below a small threshold, "
                     "and shall log peak angular rate for post-mission review.")

# 12. REQ-CMP-071: gold-defect merge (compound object + duplicate atomic) - trim 3->1
r = by_id["REQ-CMP-071"]
r["nuclear_sentences"] = [
    "In degraded payload power mode, the payload telemetry encoder shall prioritize transmission of all critical status words and any EO/IR thumbnail frames queued since the last successful downlink."
]

# 13. REQ-CMP-091: gold-defect merge (no conjunction present, duplicate restatement) - trim 2->1
r = by_id["REQ-CMP-091"]
r["nuclear_sentences"] = [
    "During degraded geofence-monitor operation, the RTL guidance module shall constrain return-to-launch climb rate using barometric altitude with a 15 m/s ceiling for the battery state-of-charge condition."
]

# 14. REQ-CMP-077: fix stray mid-sentence period/lowercase bug + missing "and"
r = by_id["REQ-CMP-077"]
r["requirement"] = ("As defined for the adjacent operator alert panel interface in REQ-SUB-083, the command-uplink console shall accept at most 10 roll commands per minute, "
                     "and it shall log each accepted command, "
                     "and when the measured value exceeds 200, a higher uplink latency than the baseline telemetry path shall be reported, "
                     "and the fastest operator override shall take precedence over any queued mission waypoint update.")

# 15. REQ-CMP-080: insert "and" before "the alert state..." and "the notification..."
r = by_id["REQ-CMP-080"]
r["requirement"] = ("When an unacknowledged critical alert persists on the operator alert panel, corrective action shall be taken, "
                     "and the alert state shall be logged, "
                     "and the notification shall be escalated to the mission supervisor.")
r["nuclear_sentences"][-1] = "The notification shall be escalated to the mission supervisor."

# 16. REQ-CMP-081: insert "and" + "the" before "operator guidance..."
r = by_id["REQ-CMP-081"]
r["requirement"] = ("While the command-uplink console operates in degraded mode, link recovery parameters shall be applied as specified elsewhere, "
                     "and the operator guidance shall be displayed promptly, "
                     "and degraded telemetry fields shall be retained until reconnection.")

with open("fw_vtol_requirements_dataset.jsonl", "w", encoding="utf-8") as f:
    for r in recs:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print("Applied 16 targeted fixes.")
