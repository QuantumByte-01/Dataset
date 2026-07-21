# FW-VTOL Requirements Dataset — Summary

**Total records:** 250
**Output:** `fw_vtol_requirements_dataset.jsonl`

## Difficulty buckets (from plan)

- precise: 50
- amb12 (1–2 ambiguity sites emphasis): 100
- amb3plus (>2 obligations and/or >2 sites): 100

## Ambiguity class

- precise: 50
- ambiguous: 136
- vague: 64

## Hierarchy level

- mission: 10
- system: 45
- subsystem: 100
- component: 95

## Axis 1 (nature)

- constraint: 35
- functional: 66
- interface: 58
- non_functional_maintainability: 7
- non_functional_reliability_availability: 33
- non_functional_safety: 26
- non_functional_security: 12
- non_functional_usability: 13

## Axis 2 (behavior & structure)

- domain_semantics_heavy: 28
- event_driven: 51
- hybrid_continuous: 19
- probabilistic: 25
- quantitative: 60
- state_driven: 50
- structural: 17

## Other stats

- Records with non-empty `context_refs`: 35
- `num_sites` distribution: {0: 50, 1: 57, 2: 70, 3: 31, 4: 16, 5: 26}
- `nuclear_sentences` length distribution: {1: 102, 2: 70, 3: 38, 4: 33, 5: 7}

## Shards merged

- `00_integration`: 15 records
- `01_airframe_aerostructures`: 23 records
- `02_propulsion`: 23 records
- `03_tilt_actuation`: 23 records
- `04_power_energy`: 23 records
- `05_flight_control_system`: 23 records
- `06_navigation_sensing`: 24 records
- `07_datalink_comms`: 24 records
- `08_payload`: 24 records
- `09_ground_control_station`: 24 records
- `10_safety_flight_termination`: 24 records

## Grounding note

Primary grounding: METU PhD thesis (tilt-wing/tilt-tail FW-VTOL, 6 rotors,
9.5 kg MTOW, 2.5 kg payload) plus Ducard & Allenspach hybrid VTOL review.
GCS / datalink / FTS threads extend beyond thesis literal text using
`grounding_facts.md` and standard light-UAS practice (e.g. STANAG 4703
payload non-interference, geofence/RTL/FTS contingency patterns) without
contradicting the primary aircraft configuration.

## Verification / regeneration

Shard-level automated validation (schema fields vs plan, taxonomy ids,
verbatim triggers, nuclear_sentences counts) was run via `validate_shard.py`.
Any records that failed were regenerated before merge; see individual shard
agent reports and `consistency_report.md` for cross-requirement findings.

## Quality finalization (sign-off)

Re-audited the full 250 against the same bar as early shards (`quality_audit.py`):

| Check | Result |
|--------|--------|
| Hard schema / plan / taxonomy / trigger / parent / context order | **0 problems** |
| Duplicate requirement texts | **0** |
| Topic-hint leaks / empty reqs / short nuclears | **0** |
| Taxonomy type coverage | **24 / 24** |
| Precise nuclear drift | **0** |
| Shall-style register | **248 / 250** (2 intentional `may optionally` vague-modal records) |
| Early vs late prose | Late shards match early median length/explanation quality after soft fixes |

Soft fixes applied before this final merge:
- Stronger discourse cues on `REQ-SUB-071`, `REQ-CMP-011`
- Expanded 9 thin ambiguity explanations in the safety/FTS shard

Remaining `consistency_report.md` note (1 Hz / 10 Hz vs 50 Hz) is retained on purpose —
those rates apply to monitoring/telemetry channels, not the 50 Hz control loop.

**Status: FINAL** — `fw_vtol_requirements_dataset.jsonl` is the deliverable.
