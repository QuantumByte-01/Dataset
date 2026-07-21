# FW-VTOL UAV — Grounding Facts Sheet

Authoritative facts for dataset generation. Derived primarily from the two
source PDFs in `input_pdfs/`. Requirements MUST stay consistent with these
numbers (a few mild inconsistencies across records are acceptable per the task
spec, but do not contradict the PDF's core design).

## Primary source — `index.pdf`
**"Design and Analysis of a VTOL Tilt-Wing UAV"** — Hasan Çakır, PhD thesis,
Middle East Technical University (METU), July 2020, Supervisor Prof. Dr. D.
Funda Kurtuluş. This is the PRIMARY grounding aircraft ("the air vehicle").

### Configuration
- **Tilt-wing + tilt-tail** hybrid FW-VTOL UAV.
- **Six fixed rotors**: four on the main wing, two on the horizontal tail.
- Main wing and horizontal tail **tilt through 90°** (vertical ↔ horizontal).
- Uses **both aerodynamic and thrust forces** during VTOL, transition, and
  forward (cruise) flight — three flight regimes.
- Fuselage length **1.8 m**, fuselage equivalent diameter **0.2 m**.
- Center of gravity ~**3 cm forward** of a reference point.

### Mass / payload budget
- Target design / take-off weight: **9.5 kg** (MTOW kept **< 10 kg**).
- Payload target: **2.5 kg**.
- Structural parts ~**2 kg**; electronic components ~**1 kg**.
- Maximum total thrust need: **15 kg-force** (thrust-to-weight ≈ 1.5).

### Propulsion / power
- Power loading target **300 W/kg** → total power ≈ **2700 W**.
- LiPo battery pack (thesis references LiPo cells, high C-rate).
- Endurance target: **> 60 min**.

### Performance envelope
- Cruise speed: **15–25 m/s**.
- Transition speed band: roughly **0–16 m/s** (accelerating through transition).
- Full operating velocity range considered: **0–40 m/s**.
- Vertical velocity in hover/linear analysis: **−5 to +5 m/s**.
- Pitch rate bound in transition analysis: ~**5 deg/s**.
- Operational radius (comparable class): ~**1 km**.

### Modeling / control
- **Nonlinear six-degree-of-freedom (6-DoF)** model in
  MATLAB/Simulink/Simscape, with a 3D CAD model; blocks: world block,
  6-DoF joint, 3D model.
- Aerodynamic analysis in **ANSYS Fluent v18** (CFD).
- **Eight (8) trim points** identified for the full mission profile; a
  separate controller designed for each trim condition.
- **Gain scheduling** between trim points for smooth transition.
- Controllers: **PID and LQR** (three robust-controller variants compared).
- Representative control-loop rate: **50 Hz**.
- Transition is the key challenge (vertical→horizontal and vice-versa);
  minimize steady-state error, avoid altitude loss during transition
  (e.g. bounded altitude deviation, ~15 cm order in sim results).

### Actuator / control-surface limits (nonlinear model, index.pdf)
- Aileron travel: **−30° to +30°**.
- Elevator travel: **−30° to +30°**.
- Tilt-wing angle: **0° to 90°**.
- Tilt-tail angle: **0° to 90°**.
- Rotor speed order-of-magnitude: up to **~8842 RPM** (front-right root motor
  example value from the nonlinear model trim table).
- Actuator transient dynamics modeled via a transfer function (first/second
  order lag) — do not need the exact equation, just that actuators have
  bounded slew/response, not instantaneous.

### Reference/benchmark aircraft named in the thesis (do NOT attribute their
### numbers to the primary aircraft; use only for sibling/context flavor)
- NASA **GL-10** Greased Lightning: ~30 kg, 15–30 m/s.
- **SUAVI**: 4.5 kg, four rotors, tilt-wing.
- **QTW-UAV**: 24 kg, 0–40 m/s.
- **QUX-02A**: 4.2 kg, two wings + four rotors, 10–25 m/s.
- **FS4 QTW-UAS**: 4.2 m wingspan, 25 m/s cruise, 47 kg MTOW, 8 kg payload.
- **AVIGLE**, **SUAVI** referenced as tilt-wing peers.

## Secondary source — Ducard & Allenspach (2021)
**"Review of designs and flight control techniques of hybrid and convertible
VTOL UAVs"** (*Aerospace Science and Technology*, Elsevier). Use for
platform-taxonomy and control-architecture flavor.

- Three convertible platform families: **tailsitter**, **tiltrotor**,
  **tiltwing**.
- Modeling: common **6-DoF translational and rotational** dynamics, plus
  vehicle-specific aerodynamic modeling.
- **State-trim / state-reference** analysis for flight phases.
- Control: **scheduled** (gain-scheduled between operating points) vs
  **unified** control approaches; **controller-scheduling policies**.
- **Control allocation**: mapping virtual control (forces/moments) to actuators
  (rotor thrusts, tilt angles, control surfaces); allocation with/without rotor
  tilt angle; direct allocation.

## Plausible subsystem decomposition (for hierarchy grounding)
Use these as subsystem/component anchors (consistent with the PDFs; some are
reasonable domain extensions):
- **Airframe & Aerostructures** (wing, tilt-tail, fuselage, tilt mechanism).
- **Propulsion** (6 rotors/motors, ESCs, propellers).
- **Tilt-actuation subsystem** (wing/tail tilt servos, 0–90°).
- **Power & Energy** (LiPo pack, BMS, power distribution).
- **Flight Control System / FCS** (autopilot, 6-DoF control laws, gain
  scheduling, PID/LQR, control allocation, 50 Hz loop).
- **Navigation & Sensing** (IMU, GNSS/GPS, magnetometer, airspeed/pitot,
  barometric altimeter, AGL rangefinder).
- **Datalink & Comms** (C2 radio link, telemetry, ground control station/GCS).
- **Payload** (EO/IR camera / surveillance sensor, ≤ 2.5 kg).
- **Ground Control Station (GCS)** (operator interface, mission planning).
- **Safety & Flight Termination** (geofence, return-to-launch, parachute/FTS).

## Flight modes / states (for state-driven requirements)
`OFF → PREFLIGHT/STANDBY → VERTICAL_TAKEOFF (hover) → TRANSITION_FWD →
FORWARD_FLIGHT (cruise) → TRANSITION_BACK → HOVER → VERTICAL_LANDING`,
plus contingency modes `RETURN_TO_LAUNCH`, `FAILSAFE/FLIGHT_TERMINATION`.

## Requirement-writing conventions (grounding from web search)
Keep `requirement` and `nuclear_sentences` in these registers.
- **EARS** (Easy Approach to Requirements Syntax) patterns:
  - Ubiquitous: "The <system> shall <response>."
  - Event-driven: "When <trigger> [<precondition>] the <system> shall <response>."
  - State-driven: "While <state>, the <system> shall <response>."
  - Unwanted behavior: "If <condition>, then the <system> shall <response>."
  - Optional: "Where <feature>, the <system> shall <response>."
- **NASA FRETISH** field order: scope · condition · component · shall · timing ·
  response (e.g. "In flight mode the battery shall always satisfy voltage > 9").
- **Standards flavor** (for `constraint`/airworthiness reqs): STANAG 4703
  (fixed-wing light UAS, MTOW ≤ 150 kg), STANAG 4746 (small VTOL UAS),
  STANAG 4671 (USAR), DO-178C (software), DO-160 (environmental), MIL-STD-810
  (environmental), MIL-STD-461 (EMC/EMI).

Sources: index.pdf (Çakır 2020 METU thesis); Ducard & Allenspach 2021 review;
EARS (Mavin & Wilkinson); NASA FRET/FRETISH; NATO STANAG 4703/4671/4746.
