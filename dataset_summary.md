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

## nuclear_sentences_v2 algorithm compatibility (post-hoc pass)

A collaborator's `nuclear_sentences_v2` requirements-decomposition tool
(rule-based: regex + spaCy POS/dependency parsing, no LLM) was reconstructed
from 50 screenshots (the real code is not present on this machine) into
`nuclear_sentences_v2_ALGORITHM_SPEC.md`. A compatibility oracle
(`nuclear_lite.py`, validated against every worked example in the source
docs) was run over all 250 requirements to check whether their phrasing
stays inside that tool's closed vocabulary and single-sentence assumption.

| Check | Before | After |
|---|---|---|
| Requirement text spans >1 sentence (tool takes one sentence per call) | 77 | **0** |
| Uses a condition/purpose phrase outside the tool's 18-word subordinator registry | 9 | **0** |
| Uses a modal outside the tool's 7-word closed set (shall/must/can/may/will/should/would) | 0 | 0 |

81 records (32%) were rewritten via 9 parallel sub-agents (grouped by
subsystem) to merge multi-sentence discourse text into one grammatical
sentence and replace non-registry condition phrasing, preserving `id`,
`hierarchy`, `axis1_nature`, `axis2_behavior`, `context_refs`, ambiguity
class/sites/types, and the same set of atomic obligations throughout. Full
before/after schema re-validation: **0 problems**, same distribution as the
original sign-off above.

### Pass 2 — independent audit, deep-trace verification, final score

A second pass: an independent sub-agent re-audited the algorithm spec
against all 50 source images (found and corrected 3 real errors, notably
that rule R7 is the tool's mechanism for handling nested embedded triggers
within a conjunction branch — not "right starts with modal" as first
drafted). Every `ATOMIC_COUNT_MISMATCH` was then root-caused rather than
accepted at face value; 18 records had a genuine issue (9 Oxford-comma
bundles the tool can't chain-split on bare commas, 6 pre-existing
gold-annotation defects — duplicate/near-duplicate atomics unrelated to the
algorithm, 1 stray-period text bug, 2 records reworded to keep a closed-set
modal without losing their ambiguity annotation) and were fixed; the rest
traced to documented limitations of the compatibility oracle itself
(no spaCy, no R7/recursive-descent implementation), not the dataset.

**Final score:**

| Check | Result |
|---|---|
| Single-sentence / closed-set-modal / registry-condition compliance | 250/250 (100%) each |
| Raw lite-oracle exact atomic-count match | 151/250 (60.4%) |
| **Estimated real-tool compatibility** | **~240/250 (~96%)** |

See `algorithm_compatibility_report.md` for the full methodology, the
per-cause mismatch breakdown, and an honest accounting of why the 96%
figure is a well-argued estimate rather than a measurement against the real
(unavailable) code.
