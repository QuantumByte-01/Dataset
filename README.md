# FW-VTOL UAV Requirements Dataset

Synthetic-but-grounded dataset of **250** natural-language requirements for a fixed-wing VTOL (FW-VTOL) UAV, with gold annotations for hierarchy, Axis-1 / Axis-2 categories, discourse `context_refs`, ambiguity/vagueness sites, and nuclear (atomic) decompositions.

**Primary deliverable:** [`fw_vtol_requirements_dataset.jsonl`](fw_vtol_requirements_dataset.jsonl)

| Resource | Purpose |
|----------|---------|
| `fw_vtol_requirements_dataset.jsonl` | Final 250-record dataset |
| `dataset_summary.md` | Counts by ambiguity / hierarchy / axis |
| `dataset_plan.json` | Deterministic generation plan |
| `ambiguity_taxonomy.yaml` | Allowed ambiguity type/family ids (from handbook images) |
| `requirement_categories.yaml` | Axis 1 (nature) + Axis 2 (behavior) only |
| `grounding_facts.md` | Authoritative aircraft facts from the PDFs |
| `consistency_report.md` | Cross-requirement consistency scan |
| `inconsistency_samples.md` | Quoted inconsistency examples |
| `shards/` | Per-subsystem generation shards |
| `batches/` | Batch specs for parallel generation |

## Grounding

- Primary: METU PhD thesis — tilt-wing / tilt-tail FW-VTOL, 6 rotors, 9.5 kg MTOW, 2.5 kg payload  
- Secondary: Ducard & Allenspach hybrid VTOL review  
- Extensions (GCS / datalink / FTS) stay consistent with `grounding_facts.md` and light-UAS practice

## Schema (per line)

Each JSONL record has: `id`, `requirement`, `axis1_nature`, `axis2_behavior`, `hierarchy`, `context_refs`, `ambiguity`, `nuclear_sentences`.  
See `dataset_schema.md` for hard rules.

---

## Mild inconsistencies (retained on purpose)

Real requirement sets are imperfect. A few mild cross-requirement tensions were **kept** so the RF pipeline can encounter them. Full quoted text is also in [`inconsistency_samples.md`](inconsistency_samples.md).

### Index — which samples / which IDs

| # | Inconsistency | Requirement IDs involved | Where (threads) |
|---|---------------|--------------------------|-----------------|
| 1 | Control / reporting **rate** (50 Hz vs 10 Hz vs 1 Hz) | `REQ-SYS-012`, `REQ-SYS-045`, `REQ-SUB-008`, `REQ-CMP-027` | Propulsion / safety monitor / airframe / tilt |
| 2 | **Endurance** bound (“exceeding” vs “at least” 60 min) | `REQ-ML-002`, `REQ-SYS-018` | Mission / power-energy |
| 3 | **Safe-state** vs geofence **RTL** priority | `REQ-SYS-042`, `REQ-SYS-043` | Safety / flight termination |
| 4 | **Link-loss / RTL** timing language | `REQ-SYS-033`, `REQ-CMP-059`, `REQ-ML-007` | Datalink / mission / C2 watchdog |
| 5 | **Mass envelope** (9.5 kg design MTOW phrasing) | `REQ-ML-001`, `REQ-SYS-004`, `REQ-SYS-034` | Mission / integration / payload |
| 6 | **Payload** hard 2.5 kg vs vague capacity wording | `REQ-ML-001`, `REQ-ML-003`, `REQ-CMP-066`, `REQ-CMP-075` | Mission / payload components |

---

### Sample 1 — Loop / reporting rate (50 Hz vs 10 Hz vs 1 Hz)

A verifier may read these as conflicting **control-loop** rates if it does not treat them as different channels.

**`REQ-SYS-012`** (propulsion @ 50 Hz)

> The propulsion system shall execute per-rotor thrust commands issued by the flight control system at the 50 Hz control-loop rate.

**`REQ-SYS-045`** (safety monitor @ 10 Hz)

> As defined for the flight-termination interface in REQ-SYS-044, the cross-subsystem safety monitor shall sample propulsion, navigation, and flight-control health telemetry at 10 Hz and shall archive each sample in non-volatile memory. When any monitored parameter crosses an elevated limit, the monitor shall raise a fault alert to the GCS promptly and may optionally recommend activating flight termination if warranted. The monitor shall maintain cross-subsystem telemetry coverage throughout autonomous flight with availability restored shortly after any detected outage.

**`REQ-SUB-008`** (airframe reporting @ ≥1 Hz)

> The airframe aerostructures subsystem shall report the mount position and the load at each propulsion and tilt mounting interface to the ground control station at a rate of at least 1 Hz. It shall poll three strain sensors on each interface and shall hand over an exceedance notice to the flight control system whenever the measured strain crosses the design limit.

**`REQ-CMP-027`** (tilt encoder @ 10 Hz)

> While the tilt-actuation subsystem is in the preflight/standby state, the tilt-position encoder shall transmit its raw zero-reference reading to the flight control system at 10 Hz.

---

### Sample 2 — Endurance (“exceeding” vs “at least” 60 min)

Mild clash at the exact 60-minute boundary.

**`REQ-ML-002`**

> The air vehicle shall provide an operational endurance exceeding 60 minutes at a cruise speed between 15 and 25 m/s, and its range shall be sufficient to complete the mission profile to be determined by the operator prior to launch.

**`REQ-SYS-018`**

> When the air vehicle executes the full eight-trim-point mission profile from vertical takeoff to vertical landing, the power and energy subsystem shall size the LiPo battery pack's stored energy to sustain a flight endurance of at least 60 minutes at the 2700 W design power loading.

---

### Sample 3 — Safe-state vs geofence / RTL priority

Competing recovery policies if a fault occurs **inside** the geofence.

**`REQ-SYS-042`**

> When any unrecoverable fault is detected during autonomous flight, the air vehicle shall enter the predefined safe state within 500 ms by commanding zero thrust on all six rotors, holding the tilt-wing and tilt-tail at their instantaneous commanded angles, and neutralizing aileron and elevator deflection to 0 degrees.

**`REQ-SYS-043`**

> The geofence monitor shall not command return-to-launch while the aircraft remains inside the approved mission geofence, and it shall notify the ground station when RTL is the nearest contingency maneuver for boundary recovery.

---

### Sample 4 — Link-loss / RTL timing language

Different numeric windows and vague “critical fault” triggers across threads.

**`REQ-SYS-033`** (C2 lost >3 s → RTL)

> If the command-and-control link is lost for longer than 3 seconds, the flight control system shall command the air vehicle to enter return-to-launch, the receiver shall continue attempting to reacquire the link at fixed intervals, and the flight control system shall report link-loss status to the operator once contact is restored.

**`REQ-CMP-059`** (watchdog expires again → power cut / alert)

> When the link-loss watchdog timer expires again after a prior reset, the link-loss watchdog timer shall command the C2 radio transceiver to reduce transmit power, and shall log the repeated expiration event with a timestamp, and shall alert the operator that the datalink has failed a second time.

**`REQ-ML-007`** (critical fault → RTL, no timer)

> The air vehicle shall continuously monitor its health status, including datalink and battery condition, throughout the mission. While the gravest fault condition is active, the air vehicle shall not proceed beyond the point of safe return. When a critical fault is detected, the air vehicle shall initiate return-to-launch.

---

### Sample 5 — Mass envelope (9.5 kg MTOW)

Design MTOW stated as 9.5 kg across mission / budget / payload (compatible with grounding, but a dual-ceiling checker may still flag related phrasing elsewhere).

**`REQ-ML-001`**

> When commanded to execute an assigned mission, the air vehicle shall complete the full vertical-takeoff-to-cruise-to-vertical-landing mission profile in a single continuous flight while carrying a payload of up to 2.5 kg, using its six-rotor tilt-wing and tilt-tail configuration and a maximum take-off weight of 9.5 kg.

**`REQ-SYS-004`**

> Whenever a subsystem's mass or power allocation changes, the systems engineering team shall update the mass and power budget promptly to keep the total within the 9.5 kg maximum take-off weight and 2700 W power loading target. The power budget shall reserve as low as possible unallocated margin, to account for estimation uncertainty, across the propulsion, power, flight control, navigation, and payload subsystems.

**`REQ-SYS-034`**

> The payload subsystem shall provide a ventilated fuselage bay that accommodates the EO/IR gimbal camera and secures it through the payload mounting plate, and it shall limit installed payload mass to 2.5 kg without exceeding the 9.5 kg MTOW budget.

---

### Sample 6 — Payload: hard 2.5 kg vs vague capacity wording

Hard mass caps coexist with vaguer “sufficient” / optional vent language.

**`REQ-ML-001`** / **`REQ-ML-003`** — hard **2.5 kg** payload mass  

**`REQ-CMP-066`** — “frame rate **sufficient** for operator tracking within a **short interval**”  

**`REQ-CMP-075`** — vent “**may optionally** remain partially open … **if needed** … closed **approximately** before takeoff”

---

## Distribution (250)

- Precise: 50  
- 1–2 ambiguity sites (amb12): 100  
- Bundled / 3+ sites or obligations (amb3plus): 100  
- Hierarchy: mission 10 · system 45 · subsystem 100 · component 95  

See `dataset_summary.md` for Axis-1 / Axis-2 counts and quality sign-off.
