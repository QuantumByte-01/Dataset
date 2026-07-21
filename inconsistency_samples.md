# Inconsistency samples (mild — retained on purpose)

## Loop / reporting rate (50 Hz control vs 10 Hz / 1 Hz monitoring)

Primary FCS loop is specified at 50 Hz, but other requirements also state 10 Hz and 1 Hz rates without saying they are a different channel — a verifier could read them as conflicting control-loop rates.

**REQ-SYS-012**

> The propulsion system shall execute per-rotor thrust commands issued by the flight control system at the 50 Hz control-loop rate.

**REQ-SYS-045**

> As defined for the flight-termination interface in REQ-SYS-044, the cross-subsystem safety monitor shall sample propulsion, navigation, and flight-control health telemetry at 10 Hz and shall archive each sample in non-volatile memory. When any monitored parameter crosses an elevated limit, the monitor shall raise a fault alert to the GCS promptly and may optionally recommend activating flight termination if warranted. The monitor shall maintain cross-subsystem telemetry coverage throughout autonomous flight with availability restored shortly after any detected outage.

**REQ-SUB-008**

> The airframe aerostructures subsystem shall report the mount position and the load at each propulsion and tilt mounting interface to the ground control station at a rate of at least 1 Hz. It shall poll three strain sensors on each interface and shall hand over an exceedance notice to the flight control system whenever the measured strain crosses the design limit.

**REQ-CMP-027**

> While the tilt-actuation subsystem is in the preflight/standby state, the tilt-position encoder shall transmit its raw zero-reference reading to the flight control system at 10 Hz.


## Endurance bound phrasing (exceeding vs at least 60 min)

Mission-level says endurance *exceeding* 60 min; a derived system req says *at least* 60 min. Mild logical tension at the exact 60-minute boundary.

**REQ-ML-002**

> The air vehicle shall provide an operational endurance exceeding 60 minutes at a cruise speed between 15 and 25 m/s, and its range shall be sufficient to complete the mission profile to be determined by the operator prior to launch.

**REQ-SYS-018**

> When the air vehicle executes the full eight-trim-point mission profile from vertical takeoff to vertical landing, the power and energy subsystem shall size the LiPo battery pack's stored energy to sustain a flight endurance of at least 60 minutes at the 2700 W design power loading.


## Safe-state vs geofence/RTL contingency priority

One req forces a hard safe-state (zero thrust / hold tilt) on unrecoverable fault; another says the geofence monitor shall *not* command RTL while inside the fence and shall notify GCS when RTL is the 'nearest' contingency — competing recovery policies if a fault occurs inside the fence.

**REQ-SYS-042**

> When any unrecoverable fault is detected during autonomous flight, the air vehicle shall enter the predefined safe state within 500 ms by commanding zero thrust on all six rotors, holding the tilt-wing and tilt-tail at their instantaneous commanded angles, and neutralizing aileron and elevator deflection to 0 degrees.

**REQ-SYS-043**

> The geofence monitor shall not command return-to-launch while the aircraft remains inside the approved mission geofence, and it shall notify the ground station when RTL is the nearest contingency maneuver for boundary recovery.


## Link-loss / RTL timing language

Contingency timing is stated with different numeric windows or vague triggers across datalink vs safety threads.

**REQ-SYS-033**

> If the command-and-control link is lost for longer than 3 seconds, the flight control system shall command the air vehicle to enter return-to-launch, the receiver shall continue attempting to reacquire the link at fixed intervals, and the flight control system shall report link-loss status to the operator once contact is restored.

**REQ-CMP-059**

> When the link-loss watchdog timer expires again after a prior reset, the link-loss watchdog timer shall command the C2 radio transceiver to reduce transmit power, and shall log the repeated expiration event with a timestamp, and shall alert the operator that the datalink has failed a second time.

**REQ-ML-007**

> The air vehicle shall continuously monitor its health status, including datalink and battery condition, throughout the mission. While the gravest fault condition is active, the air vehicle shall not proceed beyond the point of safe return. When a critical fault is detected, the air vehicle shall initiate return-to-launch.


## Mass envelope (9.5 kg design vs <10 kg)

Design MTOW 9.5 kg vs envelope '<10 kg' appear together across the set — usually compatible, but a strict checker may flag dual ceilings.

**REQ-ML-001**

> When commanded to execute an assigned mission, the air vehicle shall complete the full vertical-takeoff-to-cruise-to-vertical-landing mission profile in a single continuous flight while carrying a payload of up to 2.5 kg, using its six-rotor tilt-wing and tilt-tail configuration and a maximum take-off weight of 9.5 kg.

**REQ-SYS-004**

> Whenever a subsystem's mass or power allocation changes, the systems engineering team shall update the mass and power budget promptly to keep the total within the 9.5 kg maximum take-off weight and 2700 W power loading target. The power budget shall reserve as low as possible unallocated margin, to account for estimation uncertainty, across the propulsion, power, flight control, navigation, and payload subsystems.

**REQ-SYS-034**

> The payload subsystem shall provide a ventilated fuselage bay that accommodates the EO/IR gimbal camera and secures it through the payload mounting plate, and it shall limit installed payload mass to 2.5 kg without exceeding the 9.5 kg MTOW budget.


## Payload mass: hard 2.5 kg vs vague capacity wording

Hard 2.5 kg limits coexist with vaguer payload-capacity language elsewhere.

**REQ-ML-001**

> When commanded to execute an assigned mission, the air vehicle shall complete the full vertical-takeoff-to-cruise-to-vertical-landing mission profile in a single continuous flight while carrying a payload of up to 2.5 kg, using its six-rotor tilt-wing and tilt-tail configuration and a maximum take-off weight of 9.5 kg.

**REQ-ML-003**

> The air vehicle shall carry three payload sensors within its payload bay, not exceeding a total payload mass of 2.5 kg, and shall prioritize carriage of the highest-priority sensor package when the full complement cannot be accommodated.

**REQ-CMP-066**

> The fuselage payload bay shall accommodate the EO/IR gimbal camera on the payload mounting plate again after field swap, and during FORWARD_FLIGHT the camera shall deliver stabilized imagery at a frame rate sufficient for operator tracking within a short interval after gimbal cue commands.

**REQ-CMP-075**

> The payload bay vent may optionally remain partially open during ground checkout if needed and might be closed approximately before takeoff when ambient conditions permit.

