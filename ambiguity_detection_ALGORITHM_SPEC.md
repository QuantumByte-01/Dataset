# ambiguity_detection — Reconstructed Algorithm Spec

> Source: 37 photos of a collaborator's screen, showing the `ambiguity_detection`
> module (Python package `ambiguity_detection/` under
> `services/requirements_api/app/req/RF_product/code/disambiguation_stage`),
> its `schemas.py`, an `implementation_report.md`, and the authoritative
> `AD_ALGORITHM.md` reference doc, plus JSON output samples. The real code is
> **not** present on this machine — this is a reconstruction, the same
> methodology used for `nuclear_sentences_v2_ALGORITHM_SPEC.md`.
>
> **This module runs downstream of `nuclear_sentences_v2`.** Confirmed by the
> literal command:
> ```
> python3 -m ambiguity_detection.main \
>   --input Data/outputs/split_sentences_uav.json \
>   --output Data/outputs/ambiguity_annotations_uav.json \
>   --rules-dir ambiguity_detection/rules \
>   --input-format split_sentences
> ```
> `split_sentences_uav.json` is literally the `nuclear_sentences_v2` output
> schema (`flattened_atomics[]`, `triggers[]`, `sentence_type`). A schema
> adapter converts it to this module's internal `nuclear_sentences` shape.

## 0. Big picture — 10 phases per requirement

```
main.py
 └─ annotate_stage1_output()                    [annotate.py]
     ├─ Load input JSON + rules
     ├─ Schema adapter (split_sentences → nuclear_sentences, if needed)
     └─ for each requirement record → annotate_requirement_record():
         Phase 1  Feature Building        [parsing.py]
         Phase 2  Stage 1 Quality Gate    [stage1_quality.py]   ← BLOCKING gate
         Phase 3  Ambiguity Detection     [detectors/*.py]      ← 3 detectors
         Phase 4  Merge                   [merge.py]
         Phase 5  Classify                [classify.py]
         Phase 6  Grounding (Sprint 3)    [grounding.py]        ← optional
         Phase 7  Semantic Ranking (Sprint 4) [semantic_ranking.py] ← optional
         Phase 8  Site Assembly           [annotate.py → build_site()]
         Phase 9  Aggregate Roll-up       [aggregate.py]
         Phase 10 Decision Gate           [decision.py]
     └─ Serialize + write JSON output
```

Deterministic, rule-based (regex + spaCy POS/dependency parsing, YAML-driven
config), same design philosophy as `nuclear_sentences_v2`. An optional LLM
verifier exists behind `--llm-verify` but **never resolves ambiguity** — stub
mode passes hits through unchanged with no backend configured, and even with
one configured it's "post-detection verification only... not used for
resolution/ranking/hypothesis generation."

## 1. Schema adapter (split_sentences → nuclear_sentences)

Runs automatically when `--input-format split_sentences` (auto-detected via
key fields `flattened_atomics[]`/`triggers[]`/`sentence_type`). For each
`flattened_atomics[i]`:

1. Look up `governed_by` trigger IDs → extract conditional/temporal triggers.
2. `_modal_to_deontic(modal)` → `"O"` (Obligation) / `"P"` (Permission) /
   `"F"` (Forbidden) — derived straight from the modal word (shall/must/
   will/should/would → O; may/can → P; negated forms → F).
3. `_infer_template_id(gov_triggers)` → `"T01"` (no conditional/temporal
   trigger) / `"T03"` (temporal trigger family) / `"T04"` (conditional
   trigger family). (`T02` never appears in any image — likely unused by
   this inference function specifically.)
4. `_extract_slots(text, gov_triggers)` — crude regex-based slot splitting:
   - `condition` ← conditional triggers
   - `timing` ← temporal triggers + inline `_TIMING_RE`
   - `threshold` ← `_THRESHOLD_RE` (numeric + unit pattern)
   - `subject` ← text before the modal (`_MODAL_SPLIT_RE`)
   - `action` ← **the single first word** after the modal
   - `object` ← remaining text

So every atomic obligation gets exactly **8 candidate slots**: `subject,
action, object, condition, timing, constraint, agent2, threshold` (per
`Construct.role` in schemas.py). Detectors scan these 8 slot texts, not the
raw sentence.

## 2. Phase 2 — Stage 1 Quality Gate (`stage1_quality.py`) — the hard gate

Runs **before** ambiguity detection, to catch structural extraction errors
carried over from Stage 1 (`nuclear_sentences_v2`).

| Rule ID | Trigger condition | Severity |
|---|---|---|
| `STAGE1_UNSPLIT_ACTION` | More than one `ActionFrame` (root/conjoined verb phrase) detected in one atomic sentence — it should have been split further | BLOCKING |

`decide_stage1_quality()` → `STAGE1_ERROR` / `PASS`.

**If any BLOCKING error exists, all normal ambiguity detectors are skipped
entirely for that atomic sentence** — only the quality-gate hit itself is
passed downstream. This means: **every `nuclear_sentences`/`flattened_atomics`
entry must genuinely be single-action** (one root verb, or one verb with
conjoined objects — not two conjoined main verbs) or this tool silently
throws away all ambiguity annotation for that sentence.

## 3. Phase 3 — Ambiguity Detection: three parallel detectors

### 3a. Ambiguity Detector (`detect_ambiguity()`, `detectors/ambiguity.py`)
Detects triggers indicating **multiple valid interpretations** → class
`AMBIGUITY`.

| Rule category | Examples | Rule ID |
|---|---|---|
| Pronouns / anaphora | it, they, this, that | `PRONOUN_ANAPHORA` |
| Undefined acronym | any all-caps token, 2+ letters | `UNDEFINED_ACRONYM` |
| Negation scope | not, never, no, unless | `NEGATION_SCOPE` |

`PRONOUN_ANAPHORA`/`NEGATION_SCOPE` load from `lexical_triggers.yaml`.
`UNDEFINED_ACRONYM` is detected via inline regex `\b[A-Z]{2,}\b` — **this
fires on every all-caps token** (GPS, IMU, ESC, GCS, RTL, MTOW, EO/IR, ...)
unless suppressed. The suppression path (`TERM_NOT_IN_ONTOLOGY` ontology
grounding) is **currently disabled** project-wide (no ontology/glossary
available yet) — so as shipped, this rule is a known, accepted source of
high-volume noise on any domain-heavy corpus, not something a dataset should
try to "satisfy" by annotating every acronym as a real ambiguity site.

### 3b. Vagueness Detector (`detect_vagueness()`, `detectors/vagueness.py`)
Detects triggers indicating **under-specified, no clear reading** → class
`VAGUENESS`.

| Rule category | Examples | Rule ID |
|---|---|---|
| Passive voice, missing actor | "shall be executed" | `PASSIVE_MISSING_ACTOR` |
| Vague gradable adjectives | high, low, fast, slow | `VAGUE_GRADABLE_ADJ` |
| Comparatives/superlatives | higher, lower, maximum, minimum | `COMPARATIVE_SUPERLATIVE` |
| Approximators | approximately, about, roughly | `APPROXIMATOR` |

`VAGUE_GRADABLE_ADJ`/`COMPARATIVE_SUPERLATIVE`/`APPROXIMATOR` load from
`lexical_triggers.yaml`, and are **suppressed when a grounded numeric+unit is
already present in the same slot** (e.g. "high" in "high (>500 rpm)" would
not fire). `PASSIVE_MISSING_ACTOR` uses a regex fallback plus spaCy `auxpass`
dependency check when available.

### 3c. Incompleteness Detector (`detect_incompleteness()`, `detectors/incompleteness.py`)
Detects **numeric values missing an engineering unit** → class
`INCOMPLETENESS`.

| Rule category | Examples | Rule ID |
|---|---|---|
| Bare number without unit | 100, 5, 0.5 | `MISSING_UNIT` |

Any integer/decimal not immediately followed by a recognized engineering
unit (ms, seconds, Hz, %, meters, kg, degrees, Celsius, Fahrenheit, nautical
miles, kt, knots, ...) is flagged `MISSING_UNIT`.

### 3d. Optional LLM Verifier (`verify_with_optional_llm()`, `detectors/llm_verifier.py`)
Enabled by `--llm-verify`. Post-filter over all raw hits: sends each hit with
context to an LLM to confirm or discard. Stub mode by default — passes hits
through unchanged with no backend configured.

## 4. Phase 4 — Merge (`merge_trigger_hits()`, `merge.py`)

Deduplicates hits from all detectors using a **semantic merge key**:
`(ns_id, affected_slot, rule_family, phenomenon, normalized_trigger_text)`.
Different phenomena are kept separate even from the same slot (e.g.
`MISSING_UNIT` + `PASSIVE_MISSING_ACTOR` on the same slot → 2 distinct hits).
When multiple hits share the same key, the one with the **highest
`detector_confidence`** is kept, and evidence is merged from all duplicates.

## 5. Phase 5 — Classify (`classify_trigger()`, `classify.py`)

Maps each merged `TriggerHit.trigger_rule_id` to a canonical
`(ambiguity_class, phenomenon)` pair via a layered pipeline:
`default_rule_map()` (base class+phenomenon) → `_slot_aware_refine()` (slot
context corrections) → `_context_aware_refine()` (sentence-level context
refinements — e.g. a passive hit with no explicit `agent2` slot confirms
`passive_missing_actor`).

### Ambiguity classes (top-level, confirmed from source)
| Class | Meaning |
|---|---|
| `AMBIGUITY` | Multiple valid interpretations |
| `VAGUENESS` | Under-specified without alternatives |
| `INCOMPLETENESS` | Required information is absent |
| `STAGE1_ERROR` | Structural extraction error from Stage 1 |

**Note the 3-way (+1 gate) split — not the 2-way "ambiguous vs vague" our
dataset originally used.** `INCOMPLETENESS` is tracked as its own top-level
class, not folded into vagueness.

### Phenomenon taxonomy (by severity, from the severity table)
| Severity | Phenomena |
|---|---|
| BLOCKING | `stage1_wrong_action`, `stage1_unsplit_action`, `stage1_truncated_condition`, `missing_subject`, `missing_action` |
| HIGH | `referential_anaphora`, `temporal_anchor`, `passive_missing_actor`, `threshold_numeric`, `signal_qualification` |
| MEDIUM | `negation_scope`, `coordination_scope`, `lexical_polysemy`, `nominalization`, `undefined_acronym` |
| LOW | `implicit_assumption`, `pronoun_anaphora` (single antecedent), `polysemous_domain_term` |
| INFO | informational only, no action required |

Grounding-eligible phenomena (Phase 6 only touches these):
`lexical_polysemy`, `component_reference`, `signal_qualification`,
`state_or_mode_qualification`, `generality`.

Severity scale: `INFO(0) < LOW(1) < MEDIUM(2) < HIGH(3) < BLOCKING(4)`.

## 6. Phase 6 — Grounding (Sprint 3, `apply_grounding_to_hits()`, `grounding.py`)

**Optional** — only runs when `--symbols` is provided or a glossary is
loaded. For each classified hit whose phenomenon is grounding-eligible:
`ground_phrase(phrase, CorpusSymbolTable, expected_kinds, GroundingConfig)`:
normalize → score against corpus (exact canonical +0.50, exact alias +0.45,
modifier overlap +0.10-0.25, compatible kind +0.15, requirement-local ref
+0.10) → threshold filter:
- **UNIQUE** (1 candidate above threshold): `strict_authoring` policy keeps
  the hit but downgrades severity to LOW; `grounding_aware` policy suppresses
  it entirely (resolved).
- **MULTIPLE** (>1 candidate): keep hit, populate
  `hypothesis_space.candidate_readings` with the grounding candidates.
- **NONE**: `unresolved_policy` = suppress / review / emit_low_confidence.

We have no corpus/glossary for our dataset, so this phase is dormant by
default — the raw Phase 5 classification is what actually matters for us.

## 7. Phase 7 — Semantic Ranking (Sprint 4, `apply_ranking_to_hits()`, `semantic_ranking.py`)

Runs after grounding, only relevant when a hit has `candidate_readings`. For
each: rank by contextual compatibility → `RESOLVED` (suppress entirely) /
`AMBIGUOUS` (keep, `hypothesis_space.status="generated"`) / `INSUFFICIENT`
(keep, `status="unresolved"`). Also dormant without grounding.

## 8. Phase 8 — Site Assembly (`build_site()`, `annotate.py`)

Converts each surviving `TriggerHit` into a schema-compliant `AmbiguitySite`:
anchors spans in both nuclear and raw requirement text (`find_span()`),
assigns severity (`assign_severity()` priority: grounding override >
classify-time evidence > `_RULE_SEVERITY_OVERRIDES` > `_PHENOMENON_SEVERITY`
default > `"unassessed"`), attaches a natural-language repair suggestion
(`get_repair_suggestion(phenomenon)`), and maps severity → `safety_criticality`:
`BLOCKING`/`HIGH` → `high`; `MEDIUM` → `medium`; `LOW`/`INFO` → `low`.

## 9-10. Aggregate + Decision

Bottom-up count roll-up at construct/nuclear/sub-requirement/requirement
levels (`AmbiguityAggregate.counts_by_class`, `counts_by_phenomenon`,
`total_sites`). Final verdict (`decision.py`):

| Sites found | Outcome |
|---|---|
| None | `PASS` |
| Only INFO/LOW | `PASS_WITH_NOTES` |
| Any MEDIUM or HIGH | `REVIEW` — engineer review needed |
| Any BLOCKING | `FAIL` — requirement must be rewritten before use |

## 10. Output shape (per requirement)

```json
{
  "schema_version": "0.2.0",
  "requirement_ref": {"req_id": "REQ-001", "source_text_sha256": "...", "raw_text": "..."},
  "complexity": "atomic | complex",
  "template_id": "T01 | T03 | T04 | unknown",
  "nuclear_requirements": [
    {
      "ns_id": "REQ-001-NS1", "text": "...", "template_id": "T01",
      "deontic": "Obligation | Permission | Forbidden",
      "constructs": [
        {"construct_id": "REQ-001-NS1-C1", "role": "subject | action | object | ...",
         "present": true, "text": "...",
         "sites": [{"site_id": "...", "ambiguity_class": "...", ...}],
         "aggregate": {"counts_by_class": {...}, "total_sites": "N"}}
      ],
      "cross_construct_sites": [...],
      "aggregate": {...}
    }
  ],
  "aggregate": {...},
  "interpretation_space": {"status": "unresolved"}
}
```

## 11. Real quality-tuning history (from `implementation_report.md`) — validated on a 100-requirement UAV sample

| Version | Total sites | AMBIGUITY | INCOMPLETENESS | VAGUENESS | Duplicate-like | Top rules |
|---|---|---|---|---|---|---|
| Before noise reduction | 630 | 420 | 179 | 31 | 47 | `TERM_NOT_IN_ONTOLOGY`=111, `ATTACHMENT_AMBIGUITY`=101 |
| After quality fixes | 418 | 319 | 68 | 31 | 45 | `TEMPORAL_CUE`=108, `QUANTIFIER_SCOPE`=72, `POLYSEMOUS_DOMAIN_TERM`=60 |
| Current version (2026-07-09) | 291 | — | — | — | 0 | `QUANTIFIER_SCOPE`=62, `POLYSEMOUS_DOMAIN_TERM`=41, `TEMPORAL_CUE`=38 |

Quality fixes applied by the real maintainers (important precedent — these
are things they explicitly decided NOT to flag, on their own UAV corpus):
1. Disabled `TERM_NOT_IN_ONTOLOGY` entirely (commented out) — too noisy
   without a real ontology/glossary.
2. Disabled the broad `ATTACHMENT_AMBIGUITY` regex fallback — too noisy.
3. Auto-fill `target.missing_element` for `INCOMPLETENESS` sites when absent
   (was a bug producing 156 sites with no missing-element description).
4. Domain-phrase protection in `symbolic.py` — suppresses bare polysemy
   hits inside known domain phrases ("flight controller", "go-around",
   "return-to-home").
5. Grounded-threshold suppression in `lexical.py` — suppresses
   comparative/vague threshold hits when a numeric value + unit is already
   present in the same slot.
6. Temporal cue context guards — reduces bare `TEMPORAL_CUE` noise when an
   explicit anchor term is present in the same slot text.
7. Semantic dedup key change (span-sensitive → `ns_id+slot+rule_family+
   normalized_trigger`).
8. Expanded unit list (degrees/Celsius/Fahrenheit/nautical miles/kt/knots)
   to reduce `MISSING_UNIT` false positives.

## 12. Practical implications for our dataset

1. **`ambiguity.class` should be 3-way + implicit pass, not 2-way.** Real
   tool tracks `AMBIGUITY` / `VAGUENESS` / `INCOMPLETENESS` as **independent**
   per-site classes (each `AmbiguitySite` carries its own class), not one
   summary label per record. Our schema's one-class-per-record was a lossy
   simplification — every instance's existing `family` field
   (`ambiguity_taxonomy.yaml`) already deterministically maps to the correct
   real class (`vagueness`→`VAGUENESS`, `incompleteness`→`INCOMPLETENESS`,
   everything else→`AMBIGUITY`), so this is a mechanical, safe backfill.
2. **`STAGE1_UNSPLIT_ACTION` is a hard, blocking, all-or-nothing gate.** Any
   `nuclear_sentences` entry that still bundles two independent main verbs
   (not just a compound object) gets **zero** ambiguity annotation from the
   real tool, silently. Worth an explicit scan.
3. **`UNDEFINED_ACRONYM` over-triggers on every all-caps token by design**,
   and the real maintainers' own fix for this class of noise
   (`TERM_NOT_IN_ONTOLOGY`) is to disable ontology grounding rather than
   annotate every acronym — so a domain-heavy dataset like ours is *expected*
   to produce many `UNDEFINED_ACRONYM` hits the tool can't resolve on its
   own; this is a known, accepted tool characteristic, not something our
   gold annotations should try to preemptively satisfy by tagging every GPS/
   IMU/ESC mention as a real ambiguity site.
4. Slot extraction is crude (`action` = first word after the modal only) —
   this affects internal per-slot targeting, not something we can or should
   try to pre-align text for.
