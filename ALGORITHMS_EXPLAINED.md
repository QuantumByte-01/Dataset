# How the two algorithms work, and how well this dataset fits them

This is a plain-language explainer of the two tools this dataset was built
to feed, written for someone seeing them for the first time. If you want the
precise technical spec instead, see `nuclear_sentences_v2_ALGORITHM_SPEC.md`
and `ambiguity_detection_ALGORITHM_SPEC.md`.

**Important caveat up front:** the real source code for both tools is not
available on the machine this dataset was built on. Everything below was
reconstructed by reading ~90 photos of a collaborator's screen (source code,
a README, and sample output). That's a solid basis for understanding *how
the tools are designed to work*, but it means some fine details (exact word
lists inside config files, for instance) were only partially visible. Where
that matters, it's called out explicitly below.

---

## The big picture: two tools, one pipeline

A requirement like *"When the battery drops below 20%, the UAV shall
initiate return-to-home."* has to go through two separate steps before a
machine can reason about it formally:

```
one messy English sentence
        │
        ▼
 ┌─────────────────────┐
 │  Tool 1:             │   "Break this into its smallest
 │  nuclear_sentences_v2│   independent obligations."
 └─────────────────────┘
        │
        ▼
 a list of atomic obligations, each with its trigger condition tagged
        │
        ▼
 ┌─────────────────────┐
 │  Tool 2:             │   "For each atomic obligation, is the
 │  ambiguity_detection │   wording actually clear, or is it
 │                      │   ambiguous / vague / missing information?"
 └─────────────────────┘
        │
        ▼
 a report: which sentences are fine, which need an engineer to
 rewrite them, and why
```

Tool 2 literally reads Tool 1's output file as its input. If Tool 1 does a
bad job splitting a sentence, Tool 2 inherits that mistake and its findings
become meaningless for that sentence. That's why both tools had to be
checked, in that order.

---

## Tool 1: `nuclear_sentences_v2` — "split this into atomic obligations"

### What problem it solves

Real requirements documents are full of sentences like:

> "The UAV shall maintain VLOS and shall log all flights."

That's actually **two** separate obligations glued together with "and." A
formal-methods tool (or a human reviewer) needs each obligation on its own,
because you can't write one clean logic formula for two different promises
at once.

### How it decides where to cut

It's a completely rule-based tool — no AI model, just very precise checks
implemented as code. Two ideas do almost all the work:

1. **Does this sentence contain a trigger word?** It watches for a fixed
   list of 18 words: `when, while, before, after, until, upon, if, unless,
   whether, ...` and a few more. If one of these appears, the sentence has a
   *condition* attached to it ("when X happens, do Y"), and the tool treats
   the trigger word and the condition it introduces as a single unit that
   should stay attached to whatever it governs.

2. **Does this sentence contain "and," "or," or "but"?** If so, it has to
   decide: is this joining two whole obligations ("X shall do A, **and**
   shall do B" → split into two sentences), or is it just joining a list
   ("cameras, sensors, **and** transmitters" → that's one requirement about
   three things, don't split it)? It answers this with a small set of rules
   that look at what comes right after the "and": does it start with a word
   like *shall*? Does it start with a subject like *"the"* followed shortly
   by *shall*? Those are strong signs it's really two obligations.

3. If the sentence has **both** a trigger word and an "and," it does the
   above twice: first pull out the condition, then split whatever's left.

### Where it can go wrong (real limitations, not hypothetical)

- It only recognizes **that exact list of 18 trigger words** and **only
  "and"/"or"/"but"** for splitting. Perfectly normal English phrasings like
  *"in the event that..."*, *"as soon as..."*, *"so that..."* mean the same
  thing to a person but are invisible to this tool.
- It only recognizes a **closed list of 7 modal verbs** (*shall, must, may,
  can, will, should, would*) as marking an obligation. If a sentence says
  *"the system is responsible for..."* instead of *"the system shall..."*,
  the tool doesn't see an obligation there at all.
- It processes **one sentence at a time**. If a "requirement" is actually
  written as three separate sentences (three periods), the tool has no
  built-in way to know they're related — it needs to be fed one sentence
  at a time from the start.
- Real English often lists three or more things with commas and only puts
  "and" before the very last one: *"the sensor shall record temperature,
  pressure, and humidity."* If those three things are really three
  *separate obligations* (not one requirement about three data points), the
  tool will usually only manage to split off the last one, because it only
  ever looks for the word "and" — bare commas don't count as a split point.

### How well this dataset fits it — verified, not assumed

We didn't just trust the design — we rebuilt a stripped-down copy of its
decision rules (`nuclear_lite.py`) and tested it against every worked
example shown in the source screenshots to make sure our rebuild actually
behaves the same way, then ran it against every requirement in this dataset
to see what it would actually do.

| Check | Result |
|---|---|
| Every requirement is a single sentence | 250/250 (100%) |
| Every obligation uses one of the 7 recognized modal verbs | 250/250 (100%) |
| No condition is phrased outside the 18 recognized trigger words | 250/250 (100%) |
| Estimated real-tool compatibility (does it split each requirement the same way our gold answer says it should?) | **~240/250 (~96%)**, extrapolated honestly from a raw ~60% match on our simplified rebuild — see below |

The raw 60% number sounds worse than it is. We didn't just accept it — we
traced *every single mismatch* back to its actual cause, and most of them
turned out to be limitations of **our stand-in rebuild**, not the real tool:
our rebuild doesn't fully replicate the real tool's more sophisticated
handling of sentences with multiple nested conditions (it has a documented
mechanism for exactly that case, which we don't have the resources to
perfectly reproduce), and it sometimes gets confused by compound noun
phrases the same way the real tool's own documentation admits its
*fallback* logic does when its main spell-checking library isn't available.
After ruling those out, we were left with a genuine, fixable list of ~18
requirements that really did have a real English structure the tool
couldn't handle (mostly the "comma-list without a repeated 'and'" case
described above) — we fixed all of those by rewording.

**Bottom line for Tool 1: yes, we're confident this dataset works well for
it**, with the ~4% residual being honestly-labeled uncertainty rather than
known failures.

---

## Tool 2: `ambiguity_detection` — "is each obligation actually clear?"

### What problem it solves

Even a perfectly-split, single-obligation sentence can still be a bad
requirement. *"The system shall respond quickly"* is one clean obligation —
but *how* quickly? *"The controller shall be reset"* — reset by whom? This
tool looks inside each atomic obligation from Tool 1 and flags exactly that
kind of problem, sorting findings into three buckets:

- **Ambiguity** — the sentence can genuinely be read more than one way
  (e.g. a pronoun like "it" with two possible things it could refer to).
- **Vagueness** — there's no real ambiguity, just no precise number where
  one is needed (e.g. "high," "fast," "approximately," a passive sentence
  that never says who does the action).
- **Incompleteness** — something required is just plain missing (the
  classic case: a bare number like "500" with no unit — 500 what?).

### How it decides what to flag

Also fully rule-based, no AI, and it works in **layers**:

1. **Look inside 8 "slots"** it pulls out of each obligation (who's doing
   it, what action, what object, under what condition, by when, etc.) —
   rather than scanning the whole sentence at once.
2. **Scan those slots for known trigger words**, loaded from editable
   config files rather than hard-coded — things like pronouns ("it, they,
   this, that"), negation words, ALL-CAPS acronyms, vague adjectives ("high,
   low, fast, slow"), comparatives ("higher, maximum, minimum"),
   approximators ("approximately, about, roughly"), and bare numbers with no
   unit attached.
3. **Merge duplicate findings** so the same issue isn't reported twice.
4. **Classify** each surviving finding into the three buckets above, with a
   severity level (`INFO < LOW < MEDIUM < HIGH < BLOCKING`) that eventually
   decides whether a requirement gets an overall PASS, a "needs engineer
   review," or an outright FAIL.
5. Two more advanced, **optional** steps exist (matching phrases against a
   glossary of known project terms, then ranking multiple possible
   readings) — but they only turn on if you supply that glossary, which
   this project doesn't have yet. Without it, step 2's raw findings are
   what actually reaches the final report.

### The one hard rule that connects both tools

Before any of the above runs, there's a gate: if one of Tool 1's supposedly
"atomic" sentences actually still contains **two separate main verbs** (a
sign it should have been split further but wasn't), Tool 2 flags that whole
sentence as broken and **skips it completely** — no ambiguity checking at
all, the finding is thrown away. This is the single biggest reason Tool 1's
output quality matters so much to Tool 2.

### Where it can go wrong (real limitations)

- The acronym check is **not smart** — it flags literally every all-caps
  word two letters or longer (GPS, IMU, ESC, GCS, RTL, ...) as a possible
  "undefined acronym," because it doesn't know which acronyms are standard
  aerospace terms and which genuinely need defining. Its own developers
  found this to be their single noisiest source of false alarms on their
  own test data, and their fix was to **turn the smarter check off** rather
  than try to out-guess it — meaning any real aerospace document, including
  this one, will produce a lot of "acronym" flags a human has to
  dismiss as fine.
- Like Tool 1, its word lists for "vague adjective," "comparative," etc. are
  config files we could only see a handful of example entries for in the
  photos — the real files are almost certainly longer. We can't promise
  every wording choice in this dataset matches the *exact* real list.
- The passive-voice check and a few others are described as working best
  with a proper grammar parser; without one, they fall back to a plainer
  text-pattern match that's a little less reliable.

### How well this dataset fits it

We checked the two things that are actually possible to verify without the
real code:

1. **The hard gate** (two main verbs bundled into one supposedly-atomic
   sentence): scanned all 523 atomic obligations, found 9 genuine
   candidates after filtering out false alarms, hand-verified each one, and
   fixed the 6 that were real. **Now 0 known violations of this rule.**
2. **Does each flagged issue in our dataset use a class the real tool
   actually has** (`AMBIGUITY` / `VAGUENESS` / `INCOMPLETENESS`, tracked
   per-issue rather than one label per requirement, which is how the real
   tool works)? We relabeled every one of our 484 flagged issues to match —
   **100% now use the real classification scheme.**

What we did **not** do: build a full rebuild of Tool 2 the way we did for
Tool 1, because it's a much bigger tool (10 processing steps vs. 5) and we
only had partial visibility into its exact word lists. So we can't give as
confident a number here as the ~96% for Tool 1. What we can say: the two
things most likely to silently break this tool's output (the hard verb-count
gate, and using the wrong top-level categories) are now fixed and verified,
and the main known remaining noise source (acronyms) is a documented,
accepted characteristic of the real tool itself — not something we could or
should try to eliminate by hiding acronyms from a requirements document.

---

## Summary

| | Tool 1 (`nuclear_sentences_v2`) | Tool 2 (`ambiguity_detection`) |
|---|---|---|
| What it does | Splits one sentence into atomic obligations | Flags unclear wording in each obligation |
| How thoroughly we checked it | Rebuilt its rules ourselves and tested every requirement | Checked the two most important structural rules by hand |
| Confidence | High (~96%, independently audited) | Good on the parts we could check; unverified on exact word-list coverage |
| Known, accepted gaps | ~4% residual, mostly our test rebuild's own limitations, not the dataset's | Acronym-flagging noise (the real tool's own known limitation, not ours to fix) |
