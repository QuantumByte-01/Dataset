# Record schema & generation contract (READ BEFORE GENERATING)

Every generation sub-agent MUST emit records that satisfy this contract exactly.
One JSON object per line (JSONL). No trailing commas, valid JSON, UTF-8.

## Fields

```json
{
  "id": "REQ-ML-001",                    // provided by the plan; do not change
  "requirement": "Full NL text. May be multi-sentence / discourse style.",
  "axis1_nature": "<one id from requirement_categories.yaml axis1_ids>",
  "axis2_behavior": "<one id from requirement_categories.yaml axis2_ids>",
  "hierarchy": {
    "level": "mission | system | subsystem | component",   // from plan
    "parent_id": "REQ-... or null"                          // from plan; null only for mission
  },
  "context_refs": ["REQ-..."],           // ids this req depends on (see plan); [] if none
  "ambiguity": {
    "class": "precise | ambiguous | vague",
    "num_sites": 0,                       // == length of instances
    "instances": [
      {
        "type": "<taxonomy id from ambiguity_taxonomy.yaml>",
        "family": "<the family that id belongs to>",
        "trigger": "exact substring copied verbatim from requirement",
        "explanation": "one sentence: why this word/phrase is ambiguous/vague + the competing readings"
      }
    ]
  },
  "nuclear_sentences": ["Atomic obligation 1.", "Atomic obligation 2."]
}
```

## Hard rules

1. **axis1_nature / axis2_behavior**: exactly one id each, from
   `requirement_categories.yaml`. Only Axis 1 and Axis 2 are used — no Axis 3/4.
2. **ambiguity.class**:
   - `precise` → `num_sites = 0`, `instances = []`, and `nuclear_sentences`
     has exactly **1** item (single atomic obligation).
   - `ambiguous` → at least one instance whose type is from a TRUE-ambiguity
     family (syntactic_structural, lexical, referential, scopal, pragmatic).
   - `vague` → all instances are from the `vagueness` or `incompleteness`
     families (underspecified threshold/modal, not discrete readings).
   - Rule of thumb for mixed records: if ANY site is a true-ambiguity type →
     class `ambiguous`; if ALL sites are vagueness/incompleteness → class `vague`.
3. **num_sites MUST equal len(instances)**.
4. **trigger MUST be an exact, case-sensitive substring of `requirement`.**
   Copy it verbatim (including surrounding words if the ambiguity is multi-word).
5. **type / family MUST come from `ambiguity_taxonomy.yaml`.** Use the `id`
   value for `type` and its parent family key for `family`. Do not invent types.
6. **nuclear_sentences** = gold atomic decomposition of `requirement`:
   - Split coordinated predicates joined by **"and"** into separate items.
     **Never split on "or"** (a disjunction stays in one obligation).
   - Peel each conditional/`when`/`while`/`if` clause into the obligation it guards.
   - Normalize passive voice and copular "shall be" to `<actor> shall <verb> ...`
     where the actor is recoverable; if the actor is genuinely hidden, that is a
     `subject_vagueness` site — keep it but note it.
   - Each item = one actor, one action, one condition (EARS-style).
   - Precise req → 1 item. Bundled req → one item per atomic obligation.
7. **hierarchy.parent_id** must be the id given in the plan; it always refers to
   a higher level and an already-introduced id. Mission-level → `null`.
8. **context_refs**: include exactly the ids the plan tells you, AND make the
   `requirement` text genuinely depend on them (a pronoun, an elided subject,
   "the aforementioned <x>", "that subsystem", "as defined for <parent>"...).
   The referenced id is always introduced earlier. `[]` when the plan says none.

## Register / style
- Real spec-document prose. Use EARS/FRETISH shapes (see `grounding_facts.md`):
  "The <component> shall <response>", "When <trigger> the <system> shall ...",
  "While <state>, ...", "If <fault>, then ...".
- Discourse-style (hard) records should read like a systems engineer wrote a
  short paragraph: 2–4 sentences, occasional cross-reference, multiple bundled
  obligations. Not an artificially inflated single sentence.
- Ground numbers in `grounding_facts.md`. Do not contradict the primary
  aircraft (tilt-wing, 6 rotors, 9.5 kg MTOW, 2.5 kg payload, 15–25 m/s cruise,
  8 trim points, 50 Hz loop, PID/LQR, gain scheduling, >60 min endurance).
- Vary triggers across the taxonomy — do not reuse the same trigger word across
  many records. Follow the `suggested_types` the plan assigns to each record so
  the whole taxonomy gets covered.

## Worked examples

Precise (functional / event_driven):
```json
{"id":"REQ-SUB-051","requirement":"When the commanded tilt angle reaches 90 degrees, the tilt-actuation subsystem shall report transition-complete to the flight control system within 100 ms.","axis1_nature":"functional","axis2_behavior":"event_driven","hierarchy":{"level":"subsystem","parent_id":"REQ-SYS-011"},"context_refs":[],"ambiguity":{"class":"precise","num_sites":0,"instances":[]},"nuclear_sentences":["When the commanded tilt angle reaches 90 degrees, the tilt-actuation subsystem shall report transition-complete to the flight control system within 100 ms."]}
```

Vague (1 site, threshold_vagueness):
```json
{"id":"REQ-SYS-020","requirement":"The flight control system shall keep altitude deviation low during the vertical-to-forward transition.","axis1_nature":"functional","axis2_behavior":"hybrid_continuous","hierarchy":{"level":"system","parent_id":"REQ-ML-005"},"context_refs":[],"ambiguity":{"class":"vague","num_sites":1,"instances":[{"type":"threshold_vagueness","family":"vagueness","trigger":"low","explanation":"'low' gives no numeric altitude-deviation bound, so 'low' could mean under 1 m or under 5 m depending on reader."}]},"nuclear_sentences":["While transitioning from vertical to forward flight, the flight control system shall keep altitude deviation low."]}
```

Hard (bundled + multi-site, ambiguous):
```json
{"id":"REQ-SUB-060","requirement":"The power subsystem shall monitor the battery and the ESCs, and when cell voltage is critical it shall notify the operator and initiate return-to-launch. It may also possibly reduce cruise power if needed.","axis1_nature":"non_functional_reliability_availability","axis2_behavior":"event_driven","hierarchy":{"level":"subsystem","parent_id":"REQ-SYS-014"},"context_refs":[],"ambiguity":{"class":"ambiguous","num_sites":3,"instances":[{"type":"coordination","family":"syntactic_structural","trigger":"the battery and the ESCs, and when","explanation":"the two 'and's make it unclear whether monitoring covers battery+ESCs jointly and whether the voltage clause scopes both."},{"type":"threshold_vagueness","family":"vagueness","trigger":"critical","explanation":"'critical' cell voltage has no numeric threshold."},{"type":"optionality_vague_modals","family":"vagueness","trigger":"possibly","explanation":"'may also possibly ... if needed' leaves the power-reduction obligation optional and unverifiable."}]},"nuclear_sentences":["The power subsystem shall monitor the battery.","The power subsystem shall monitor the ESCs.","When cell voltage is critical, the power subsystem shall notify the operator.","When cell voltage is critical, the power subsystem shall initiate return-to-launch."]}
```
```
```
