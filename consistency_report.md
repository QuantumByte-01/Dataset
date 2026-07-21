# Cross-requirement consistency report

Scanned **250** records.

## Method

Regex extraction of shared numeric/mode parameters (MTOW, payload mass,
cruise band, endurance, control-loop Hz, tilt range, rotor count) plus
structural checks on `parent_id` / `context_refs` ordering. Benchmark
aircraft comparisons (GL-10, SUAVI, QUX-02A, FS4) are excluded from
primary-aircraft contradiction flags.

## Findings

Concrete examples (quoted) are also in `inconsistency_samples.md`.

### Possible conflict on `control_hz`
- `REQ-SYS-045`: `10 Hz` (nums=['10'])
- `REQ-SUB-008`: `1 Hz` (nums=['1'])
- `REQ-CMP-027`: `10 Hz` (nums=['10'])
- `REQ-CMP-047`: `10 Hz` (nums=['10'])

## Mild inconsistencies retained (intentional)

Real requirement sets are imperfect. Mild phrasing differences (e.g. MTOW
stated as 9.5 kg design vs <10 kg envelope; endurance '>60 min' vs
'at least 60 minutes') are retained so the RF pipeline can encounter them.

## Fixes applied

None — no silent deletions; no auto-rewrites required in this pass.

## Mode / regime vocabulary coverage

- `transition`: mentioned in 38 records
- `cruise`: mentioned in 15 records
- `return-to-launch`: mentioned in 13 records
- `forward flight`: mentioned in 11 records
- `hover`: mentioned in 11 records
- `RTL`: mentioned in 9 records
- `flight termination`: mentioned in 2 records
- `VTOL`: mentioned in 1 records
