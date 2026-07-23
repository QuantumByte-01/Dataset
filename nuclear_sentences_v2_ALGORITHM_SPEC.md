# nuclear_sentences_v2 — Reconstructed Algorithm Spec

> Source: 50 photos of a collaborator's (Akshay Pachbudhe's) screen, showing the
> `nuclear_sentences_v2` module (part of a larger "disambiguation_stage" / RF
> pipeline) — `schemas.py`, `normalizer.py`, `sentence_classifier.py`,
> `conjunction_detector.py`, `clause_analyzer.py`, `splitter.py`,
> `complex_sentence_processor.py`, `subordinator_registry.py`, `main.py`,
> `ALGORITHM.md`, `README.md`, `COMPLEX_USAGE.md`, plus one real output sample
> (`split_sentences_uav 1.json`) and one architecture slide.
>
> The actual code is **not** present on this machine (confirmed) — this document
> is a reconstruction from those images and is the single source of truth for
> everything below. It is deterministic, rule-based (regex + spaCy POS/dependency
> parsing, **no LLM/ML** at this stage — DeBERTa/transformer models seen in the
> architecture slide belong to a separate ambiguity-detection function, not this
> one).

## 0. Big picture

Input: **one raw NL requirement sentence** (a string). Output: either a flat
list of atomic clauses (`SplitResult`, for SIMPLE sentences) or a recursive
Trigger–Scope–Consequent tree that flattens to atomic sentences each tagged
with the trigger(s) that govern it (for COMPLEX sentences).

```
Raw NL sentence
  -> Step 1  Normalization
  -> Step 2  Sentence Structure Classification (SIMPLE / COMPLEX gate)
       SIMPLE  -> Step 3 Conjunction Detection -> Step 4 Conjunction
                  Classification (R1-R6) -> Step 5 Recursive Splitting
                  -> SplitResult
       COMPLEX -> Step 6 R-CLAIM (subordinator detection + scope assignment)
                  -> Step 7 Conjunction Split on main clause (reuses R1-R6, +R7)
                  -> Step 8 Recursive Descent (nested subordinators / leaves)
                  -> ClauseTree + flattened_atomics
```

## 1. Step 1 — Normalization (`normalizer.py`)

`normalize_sentence(text) -> str`

| # | Rule | Example |
|---|------|---------|
| N1 | Collapse internal whitespace runs to a single space | `"The  UAV shall"` → `"The UAV shall"` |
| N2 | Strip leading/trailing whitespace | |
| N3 | Append a period if the sentence doesn't already end with `.`/`!`/`?` | `"...VLOS"` → `"...VLOS."` |

No other rewriting at this stage.

## 2. Step 2 — Sentence Structure Classification (`sentence_classifier.py`)

`classify_sentence(sentence) -> (sentence_type, subordinators_found, temporal_subordinators, conditional_subordinators)`

**SIMPLE** = plain Subject + Predicate (NP+VP), no subordinating conjunction from
the closed set below. Eligible for conjunction splitting (Step 3+).
**COMPLEX** = contains ≥1 subordinator from the closed set. Conjunction
splitting is **skipped** — routed instead to Step 6 (complex processor).

### Closed vocabulary — the ONLY words that trigger COMPLEX (18 total)

**Temporal subordinators (12):**
`when, whenever, while, whilst, as, before, after, once, since, till, until, upon`

| word | semantic role |
|---|---|
| when | point-in-time condition / trigger |
| whenever | repeated temporal trigger |
| while | concurrent/simultaneous state |
| whilst | concurrent/simultaneous state (formal) |
| as | simultaneous action |
| before | temporal precedence |
| after | temporal succession |
| once | temporal boundary (immediate succession) |
| since | temporal origin / elapsed time |
| till | temporal boundary (informal) |
| until | temporal boundary |
| upon | immediate temporal trigger |

**Conditional subordinators (6):**
`if, unless, whether, given, without, provided`

| word | semantic role |
|---|---|
| if | conditional |
| unless | negative conditional |
| whether | conditional / alternative |
| given | presupposed condition |
| without | negative precondition |
| provided | stipulative condition |

**"since" and "as"** are ambiguous (causal-or-temporal): both still classify
COMPLEX correctly, but a `COMPLEX:AMBIGUOUS_FAMILY` warning is emitted.

**Detection**: word-boundary-anchored, case-insensitive regex scan, matches
sorted left-to-right into `subordinators_found` / split by category. A `"wh"`
substring pre-filter is a no-false-negative optimization only — it changes
nothing about which words match.

**Any other conditional/temporal phrasing is invisible to this step** — e.g.
"in the event that", "in case of", "as soon as", "so long as", "should X
occur", "provided that X occurs" (ok — "provided" is registered, but only the
single word, not the phrase), "in order to", "so that" are **not** in the
registry and will NOT trigger COMPLEX classification or trigger extraction.

### Worked examples (ground truth from the README)

| Sentence | Result |
|---|---|
| "The UAV shall maintain VLOS and shall log all flights." | SIMPLE |
| "When battery drops below 20%, the UAV shall initiate RTH." | COMPLEX (when) |
| "The UAV shall reduce speed while in degraded GPS mode." | COMPLEX (while) |
| "The UAV shall continue unless battery drops below 20%." | COMPLEX (unless) |
| "Upon detection of a fault, the system shall switch to backup." | COMPLEX (upon) |
| "Whether armed or not, the pilot shall confirm." | COMPLEX (whether) |
| "The UAV shall be registered and shall display its number." | SIMPLE |

## 3. Step 3 — Conjunction Detection (`conjunction_detector.py`, SIMPLE path)

`find_conjunctions(sentence) -> list[ConjunctionSpan]`

Scans for coordinating conjunctions as **whole words**, case-insensitive.

| Status | Words |
|---|---|
| **Active (scanned)** | `and`, `or`, `but` |
| Disabled (defined, not scanned) | `for`, `nor`, `yet`, `so` — disambiguation logic not implemented |

**Important:** the classifier treats `and`/`or`/`but` **identically** — there
is no special-cased "never split on or" behavior. Whichever of the three is
found gets the same R1–R6 treatment below. A genuine `or`-joined pair of full
independent clauses (each opening with a modal) WILL be split into two
separate atomic "shall" sentences by this tool, even though that changes an
inclusive-or obligation into two unconditional ones. This is a real,
documented blind spot of this syntactic-only stage — not a hallucination on my
part.

`ConjunctionSpan` fields: `conjunction, char_start, char_end, left_text,
right_text, join_type (SENTENCE|LIST), confidence, signals[]`.

## 4. Step 4 — Conjunction Classification (`clause_analyzer.py`)

`classify_conjunction(span) -> ConjunctionSpan` / `analyze_conjunctions(sentence)`

6-rule priority decision tree, **first match wins**, default = LIST (0.60).

| Rule | Condition | Result | Confidence |
|---|---|---|---|
| **R1** RIGHT_STARTS_WITH_MODAL | right text opens directly with a modal phrase | SENTENCE | 0.95 |
| **R2** RIGHT_HAS_SUBJECT_THEN_MODAL | right text opens with a subject-NP starter, and a modal appears within the first 6 tokens after it | SENTENCE | 0.90 |
| **R3** RIGHT_STARTS_WITH_BARE_VERB | right text opens with a base-form verb (or adverb+base-verb), AND left text contains a modal (guard) | SENTENCE | 0.85 |
| **R4** LEFT_HAS_COMMAS_NO_MODAL | left text has comma(s) AND no modal | LIST | 0.85 |
| **R5** LEFT_NO_MODAL | left text has no modal anywhere | LIST | 0.80 |
| **R6** RIGHT_BARE_NP | right text has no modal/auxiliary and is a bare NP | LIST | 0.75 |
| DEFAULT | none of the above | LIST | 0.60 |

### Modal phrase regex (closed set — 7 words + negated forms)
```
\b(shall\s+not|must\s+not|may\s+not|cannot|shall|must|can|may|will|should|would)\b
```
**Only these count as "modal."** Periphrastic modality — "is required to", "is
responsible for", "needs to", "is to be", passive "shall be provided" (the
word "shall" is still literally present here so this one IS detected) — only
counts if one of the 7 tokens is literally present as a word.

### Subject-NP starters (for R2)
`the, a, an, this, that, these, those, its, their, his, her, our, your, my, I,
we, you, he, she, they, it`

### R3 bare-verb detection — regex fallback (used here, since spaCy is not
available in our environment; this is the documented fallback path, applied in
order):
1. First word ends `-ly` AND ≥2 words remain → adverb-led VP → SENTENCE
2. First word is numeric → quantity NP → LIST
3. First word is a non-verb starter (article/preposition/negation, closed list) → LIST
4. First word matches a noun/adjective suffix (`-tion, -ment, -al, -er, -ing`, etc.) → LIST
5. ≥2 words remain → assumed bare VP → SENTENCE; single word → LIST

### R4/R5/R6 worked examples (from the README, verbatim UAV sentences)
- "The UAV shall monitor [AND] shall log." → R1 SENTENCE (right starts with "shall")
- "The pilot shall avoid obstacles, [AND] the controller shall maintain contact." → R2 SENTENCE ("the controller" then "shall" within 6 tokens)
- "The UAV shall detect obstacles [AND] avoid them." → R3 SENTENCE (right = bare verb "avoid them"; splitter prepends subject+modal from the left clause when reconstructing: "The UAV shall avoid them.")
- "cameras, sensors, [AND] transmitters" → R4 LIST (left has commas, no modal)
- "Registration [AND] inspection are required." → R5 LIST (left "Registration" has no modal)
- "The UAV shall fly to the target [AND] return to base." → R3 SENTENCE (not R6 — "return" is a bare verb, not a noun; single-word bare nouns like "altitude"/"position" are what R6 actually catches)

## 5. Step 5 — Recursive Splitting (`splitter.py`, SIMPLE path)

Algorithm:
1. Normalize input.
2. Classify (Step 2). If COMPLEX → return unchanged (routed to Step 6 instead).
3. If SIMPLE → `analyze_conjunctions()` over the whole string.
4. Find the **leftmost SENTENCE-type** conjunction.
5. Split there: left part = first atomic sentence (normalized, period
   appended). Right part: if it starts directly with a modal phrase (R1 case,
   no explicit subject), **prepend the subject NP extracted from the left
   clause** (text before the left clause's first modal) — this is the
   "shared-subject reconstruction". Then recurse Step 3 on the reconstructed
   right part to catch further conjunctions.
6. Collect all `ConjunctionSpan` analyses from every recursive level into
   `SplitResult.conjunction_analyses`.
7. If no SENTENCE-type conjunction is found anywhere → return the whole string
   as one simple sentence.

**Worked example** (from `splitter.py` docstring):
```
"The UAV shall maintain VLOS and shall log all flights."
split at "and" (R1: right starts with modal)
left  = "The UAV shall maintain VLOS."
right_raw = "shall log all flights"
extracted subject = "The UAV"
right_reconstructed = "The UAV shall log all flights."
sentences: ["The UAV shall maintain VLOS.", "The UAV shall log all flights."]
```

`SplitResult` fields: `original, sentences[], conjunction_analyses[],
warnings[], sentence_type=SIMPLE, subordinators_found[]=[],
temporal_subordinators[]=[], conditional_subordinators[]=[]`.

## 6. Steps 6-8 — Complex Sentence Processor (`complex_sentence_processor.py`, COMPLEX path)

Builds a recursive `ClauseNode` tree. Per-node 3-step pipeline, applied
recursively:

**Step 6 — R-CLAIM** (try to claim a subordinator at the current node):
a subordinator may only be claimed if **all three** hold:
- **R-CLAIM-1**: the subordinator's span lies within this node's text (true by construction).
- **R-CLAIM-2**: the subordinator sits at the node's `front` or `end` — **not**
  buried inside one branch of a coordinated (`conj`) verb. If it's inside a
  `conj`-dependent branch, a **descendant** node (created after the
  conjunction split) claims it instead, not this node.
- **R-CLAIM-3**: after stripping the subordinate clause (full `advcl` subtree +
  the mark token), the remaining main clause is well-formed — contains a
  subject NP (`nsubj`/`csubj`, or an NP-starter heuristic) **and** a modal verb
  from the same closed 7-word set as Step 4.

If claimed → create a `Trigger {id: T#, family, subordinator, text, position
(front|end), scope (wide|narrow), confidence, formal_hint, governs_node,
governs_atomics[], signals[]}` (the real worked example's Trigger objects all
carry `confidence` and `formal_hint` — omitted from an earlier draft of this
field list), strip the subordinate clause, continue with the remaining
main-clause text.

**Trigger families** (`subordinator_registry.py`): `TEMPORAL_POINT,
TEMPORAL_DURATION, CONDITIONAL, CONTRASTIVE, CAUSAL, PURPOSE`. Ambiguous
members ("since", "as") get the special family `causal-or-temporal` +
`COMPLEX:AMBIGUOUS_FAMILY` warning. Each family has a plain-string
`formal_hint` template for annotation only (e.g. `"G({trigger} -> {consequent})"`)
— **no logic is evaluated from these**, they're just annotation strings filled
in by the caller.

**Scope assignment** (`_determine_scope`):
| condition | scope | confidence |
|---|---|---|
| position=="front" + comma after subordinate clause | wide | 0.93 |
| position=="front", no comma | wide (weakened) | 0.83 |
| position=="end" | narrow | 0.85 |

Strengthening signals: `REPEATED_MODAL_IN_MAIN`, `THEN_STARTS_MAIN`.
Weakening signals: `NEW_SUBJECT_AFTER_AND`, `SECOND_SUBORDINATOR_IN_MAIN`.

**Wide scope** = after this node's conjunction split, the trigger ID
propagates into every child's `inherited_triggers`, and ultimately into every
descendant atomic's `governed_by`. **Narrow scope** = the trigger applies to
only one branch (can produce a `COMPLEX:TRIGGER_ASYMMETRIC_ACROSS_SPLIT`
warning).

**Step 7 — Conjunction split on the (now trigger-stripped) main clause**:
reuses Steps 3-4's `analyze_conjunctions` / R1–R6 machinery directly, plus an
additional **R7 `COMPLEX_RIGHT_CLAUSE` extension (confidence 0.85)** —
"right-clause reconstruction after split" per README's Step 7 technology-
summary row. The one worked example (`COMPLEX_USAGE.md` "Case B") shows R7
firing when the right side of the split is itself a fragment that still
contains its own embedded subordinate clause (`right_text = "when the
battery level drops below 20% the flight controller shall initiate
return-to-home and shall disable non-essential payloads"` — opens with the
subordinator "when", not a modal). No image shows R7's literal source
condition, so treat its exact trigger condition as reconstructed-with-lower-
confidence, but its *purpose* is clearly to handle a conjunction branch that
carries a nested subordinate clause — i.e., **this is the tool's documented
mechanism for correctly decomposing a single sentence with multiple embedded
triggers**, not a gap. (An earlier draft of this spec mis-named R7 as
"RIGHT_STARTS_WITH_MODAL" — that was an unsupported inference; corrected
after an independent re-audit of the source images.) If a SENTENCE-type split
is found, create two child `ClauseNode` objects and recurse into each (Step 8).

**Step 8 — Recursive descent**: if no conjunction split was found but the
remaining text still contains a **claimable nested subordinator**, create a
single child node and recurse (claims the inner trigger). When no further
subordinators remain and no conjunction split applies, emit a leaf **Atomic**
sentence: `{id: S#, text, governed_by: [trigger ids], modal, source_split,
notes}`.

**ID scheme**: `ClauseNode` ids are letter-suffixed from the root (`N0`, `N0a`,
`N0b`, `N0ba`, `N0bb`, ...). Triggers are globally numbered `T1, T2, ...`.
Atomics are globally numbered `S1, S2, ...`.

**Top-level output shape** (COMPLEX case):
```json
{
  "original": "...",
  "sentence_type": "complex",
  "subordinators_found": [...],
  "temporal_subordinators": [...],
  "conditional_subordinators": [...],
  "root": { "node_id": "N0", "parent": null, "level": 0, "triggers": [...],
            "inherited_triggers": [...], "conjunction_split": {...} },
  "nodes": { "N0": {...}, "N0a": {...}, "N0b": {...}, ... },
  "flattened_atomics": [ {"id": "S1", "governed_by": [...], "modal": "shall"}, ... ],
  "warnings": [...]
}
```

Common warnings: `COMPLEX:AMBIGUOUS_FAMILY`, `COMPLEX:TRIGGER_AT_ROOT` (the
one real JSON sample shows this — a root-level trigger, i.e. the normal case
of a single front-positioned trigger governing the whole tree),
`COMPLEX:TRIGGER_AT_SUBNODE_LEVEL`, `COMPLEX:TRIGGER_ASYMMETRIC_ACROSS_SPLIT`.
README's Step 8.5 also references "multi-level trigger warning; mixed-family
warning detection" via depth-tracking/family-tracking sets — the literal
warning string for this wasn't visible in any image, so treat it as a
probable further warning class, not a confirmed one.

### R3 edge cases (from README's "correctly blocked by spaCy" table)
Four cases the *regex fallback* would misfire on but the primary spaCy path
handles correctly: `"higher remote pilot certification"` (JJR comparative,
blocked), `"has verified that all systems…"` (VBZ/AUX auxiliary not base verb,
blocked), `"successfully decoded by a receiver"` (RB+VBN+"by" passive
construction, blocked), `"fuel system and all accessories"` (NN noun
compound, blocked). Two confirmed R3-SENTENCE examples: `"...compute a
trajectory [AND] transmit it."` (VB → SENTENCE) and `"...detect [AND]
correctly classify obstacles."` (RB+VB → SENTENCE). **Since the real
deployment's primary path is spaCy, not the regex fallback, this LITE
oracle's regex-only R3 implementation is strictly more failure-prone on
noun-compound/passive edge cases than the real tool would be** — treat any
`nuclear_lite.py` mismatch that traces to R3 noun-compound confusion as
oracle noise, not a dataset defect.

## 7. Target atomic-requirement shape (from a separate whiteboard note)

```
Contextualized Atomic Requirement
├── Applicability Context/Conditions (can nest)
│     ├── Temporal condition
│     ├── Conditional trigger
│     ├── State-or-mode condition
│     ├── Location condition
│     ├── Event condition
│     └── Means/manner constraint
└── Atomic Requirement
      ├── Subject
      ├── Modality
      ├── Action
      ├── Object
      └── Performance constraints
```
This maps directly onto the algorithm's `Trigger` (= Applicability Context,
possibly nested) and `Atomic` (= Subject+Modality+Action+Object+Performance
constraints) objects above.

## 8. Practical compatibility requirements this implies for a requirements dataset

For `nuclear_sentences_v2` to actually parse a `requirement` string into the
SAME decomposition recorded as our gold `nuclear_sentences`, the text has to
stay inside this engine's closed vocabulary and single-sentence assumption:

1. **Modal closed-set**: every independent obligation clause needs a literal
   `shall/must/will/should/may/can` (or negated form) — not a periphrastic
   paraphrase ("is required to", "is responsible for", "needs to").
2. **Subordinator closed-set**: any applicability condition meant to become a
   `Trigger` governing one or more atomics must use one of the 18 registry
   words verbatim (when/while/whilst/as/before/after/once/since/till/
   until/upon/whenever, if/unless/whether/given/without/provided) — not
   "in the event that", "in case of", "as soon as", "so long as", "should X
   occur", "so that".
3. **Coordination closed-set**: only `and`/`or`/`but` are scanned for
   obligation-bundling splits — not "as well as", "in addition to",
   semicolons, "additionally". And per §3 above, `or` is split exactly like
   `and` by this tool (no semantic disjunction handling at this stage).
4. **Single-sentence input**: the module takes one sentence string at a time;
   it does not itself perform cross-period sentence segmentation. A
   `requirement` written as 2-4 separate period-delimited sentences (our
   "discourse-style" register for high-obligation records) is NOT natively
   processable end-to-end as a single call — it would need an external
   sentence-splitter to feed each sentence in separately, which changes what
   "one gold decomposition" means and loses any cross-sentence trigger scope
   (e.g. a leading temporal trigger meant to govern all following sentences).
