# Ambiguity-Detection Compatibility Report — `ambiguity_detection`

## What this is

37 photos of a collaborator's screen showed a second, downstream module —
`ambiguity_detection` — that consumes `nuclear_sentences_v2`'s output
(`split_sentences_uav.json`) and annotates each atomic obligation with
ambiguity/vagueness/incompleteness findings. See
`ambiguity_detection_ALGORITHM_SPEC.md` for the full 10-phase reconstruction.
The real code is not present on this machine; this is a reconstruction from
the images, same methodology as the `nuclear_sentences_v2` pass.

## Two concrete, justified changes made to the dataset

### 1. Per-instance `ambiguity_class` field (real 3-way taxonomy)

The real tool assigns `ambiguity_class` (`AMBIGUITY` / `VAGUENESS` /
`INCOMPLETENESS`) **per individual site**, not once per record — a record
can genuinely mix classes across its sites. Our schema only had one
record-level `class` (`precise`/`ambiguous`/`vague`), which is a lossy
simplification of the real per-site granularity.

Fix: added `ambiguity_class` to every `ambiguity.instances[]` entry,
deterministically derived from the existing `family` field (already
authoritative in `ambiguity_taxonomy.yaml` — no guessing involved):

| Family | Real class |
|---|---|
| `syntactic_structural`, `lexical`, `referential`, `scopal`, `pragmatic` | `AMBIGUITY` |
| `vagueness` | `VAGUENESS` |
| `incompleteness` | `INCOMPLETENESS` |

Result across all 250 records: **484 sites** — `AMBIGUITY`=263,
`VAGUENESS`=165, `INCOMPLETENESS`=56. The existing record-level `class`
field (`precise`/`ambiguous`/`vague`) was left in place unchanged — it's a
useful record-level summary that doesn't conflict with the new per-site
field.

### 2. `STAGE1_UNSPLIT_ACTION` gate check

The real tool's Phase 2 runs a hard, blocking quality gate on every atomic
sentence: if it detects **more than one root/conjoined main verb** in what
should be a single atomic obligation, it flags `STAGE1_UNSPLIT_ACTION`
(BLOCKING) and **skips ambiguity detection entirely** for that sentence —
silently discarding all annotation.

Scanned every `nuclear_sentences[]` entry (523 total) two ways:
1. A broad oracle-based scan (reusing `nuclear_lite.py`'s conjunction
   classifier) flagged 67 candidates — but manual inspection showed most are
   false positives from the same known regex-vs-spaCy weakness already
   documented for `nuclear_sentences_v2` (compound *noun* lists like "hover
   and cruise" or "roll angle, pitch angle... and altitude" misread as
   conjoined verbs).
2. A high-confidence filter (the closed-set modal word appears **twice** in
   one atomic sentence — unambiguous proof of two real obligations, since a
   genuine atomic sentence never needs its modal repeated) found exactly
   **9 candidates**. Each was inspected individually:
   - **6 genuine unsplit bundles**, fixed by splitting into 2 separate
     `nuclear_sentences` entries: `REQ-SYS-043`, `REQ-SYS-045`,
     `REQ-SUB-072`, `REQ-SUB-092`, `REQ-SUB-093`, `REQ-SUB-100`.
   - **3 false positives** — the second modal is inside a subordinate/
     relative/complement clause ("...cannot be accommodated...", "...for
     which structural clearance will be maintained...", "...the probability
     that the fault will propagate...") and is not a second top-level
     obligation. Left unchanged: `REQ-ML-003`, `REQ-SUB-017`, `REQ-SUB-036`.

`nuclear_sentences` count went from 517 to 523 (net +6) after the split.

## What was deliberately NOT changed

**`UNDEFINED_ACRONYM` over-triggering.** The real detector fires on every
all-caps 2+ letter token (GPS, IMU, ESC, GCS, RTL, MTOW, EO/IR, ...) unless
suppressed by ontology grounding — which the real maintainers themselves
disabled project-wide as too noisy without a real ontology (documented in
their own `implementation_report.md`: `TERM_NOT_IN_ONTOLOGY` commented out,
111 false-positive hits on their own 100-requirement sample). Our dataset is
domain-term-heavy by design (a real FW-VTOL spec necessarily is), so it will
produce many `UNDEFINED_ACRONYM` hits the tool can't resolve on its own.
This is a known, accepted characteristic of the real tool as shipped, not a
dataset defect — annotating every acronym as a formal gold ambiguity site
would misrepresent what's actually ambiguous versus what's just
under-supported tooling, so this was left alone and is documented here
instead.

## Full validation after both changes

- Schema re-validation: **0 problems** across all 250 records (same
  hierarchy/axis/taxonomy checks as every prior pass).
- Hierarchy distribution unchanged: 10/45/100/95 (mission/system/subsystem/
  component).
- `nuclear_sentences_v2` compatibility checks (single-sentence, closed-set
  modal, registry conditions) unaffected — none of these edits touched
  `requirement` text, only `nuclear_sentences` (Stage 1 decomposition) and
  the new per-site `ambiguity_class` field.
