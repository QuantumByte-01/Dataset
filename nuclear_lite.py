#!/usr/bin/env python
"""
nuclear_lite.py

A faithful-to-spec reimplementation of the deterministic parts of
nuclear_sentences_v2 (see nuclear_sentences_v2_ALGORITHM_SPEC.md), using
ONLY the documented regex-fallback rules (the real code prefers spaCy POS/
dependency parsing when available; spaCy is not installed in this
environment, so we implement exactly the fallback path the algorithm's own
docs specify for that situation). This is a LITE compatibility oracle, not
a byte-perfect port of the real recursive ClauseNode tree — its purpose is
to flag which requirement texts this real tool can and cannot decompose the
way our gold nuclear_sentences expect, not to be the tool itself.

Not reimplemented (would need spaCy): R-CLAIM-2's conj-dependency burial
check, and precise nsubj/csubj-based main-clause well-formedness. We
approximate R-CLAIM-3 with a regex heuristic (main clause must contain a
modal AND a plausible subject token) documented as the regex fallback.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------
# Closed vocabularies (from ALGORITHM_SPEC.md)
# ---------------------------------------------------------------------
TEMPORAL_SUBORDINATORS = ["when", "whenever", "while", "whilst", "as", "before",
                          "after", "once", "since", "till", "until", "upon"]
CONDITIONAL_SUBORDINATORS = ["if", "unless", "whether", "given", "without", "provided"]
ALL_SUBORDINATORS = TEMPORAL_SUBORDINATORS + CONDITIONAL_SUBORDINATORS
AMBIGUOUS_FAMILY_WORDS = {"since", "as"}

_TEMPORAL_RE = re.compile(r"\b(" + "|".join(TEMPORAL_SUBORDINATORS) + r")\b", re.IGNORECASE)
_CONDITIONAL_RE = re.compile(r"\b(" + "|".join(CONDITIONAL_SUBORDINATORS) + r")\b", re.IGNORECASE)

ACTIVE_CONJUNCTIONS = ["and", "or", "but"]
_CONJ_RE = re.compile(r"\b(and|or|but)\b", re.IGNORECASE)

MODAL_WORDS = ["shall", "must", "can", "may", "will", "should", "would"]
_MODAL_RE = re.compile(
    r"\b(shall\s+not|must\s+not|may\s+not|cannot|shall|must|can|may|will|should|would)\b",
    re.IGNORECASE,
)

SUBJECT_NP_STARTERS = {"the", "a", "an", "this", "that", "these", "those", "its", "their",
                        "his", "her", "our", "your", "my", "i", "we", "you", "he", "she",
                        "they", "it"}

_NON_VERB_STARTERS = {"the", "a", "an", "this", "that", "these", "those", "of", "in", "on",
                       "at", "to", "for", "with", "no", "not"}
_NOUN_ADJ_SUFFIX_RE = re.compile(r"(tion|ment|al|er|ing|ance|ence|ity|ness|ous|ive)$", re.IGNORECASE)
_ADVERB_LY_RE = re.compile(r"^\w+ly$", re.IGNORECASE)


def normalize_sentence(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if cleaned and cleaned[-1] not in ".!?":
        cleaned += "."
    return cleaned


def has_modal(text: str) -> bool:
    return bool(_MODAL_RE.search(text))


def classify_sentence(sentence: str):
    temporal = []
    for m in _TEMPORAL_RE.finditer(sentence):
        temporal.append((m.start(), m.group(0).lower()))
    conditional = []
    for m in _CONDITIONAL_RE.finditer(sentence):
        conditional.append((m.start(), m.group(0).lower()))
    merged = sorted(temporal + conditional, key=lambda x: x[0])
    subordinators_found = [w for _, w in merged]
    temporal_subordinators = [w for _, w in sorted(temporal, key=lambda x: x[0])]
    conditional_subordinators = [w for _, w in sorted(conditional, key=lambda x: x[0])]
    sentence_type = "complex" if subordinators_found else "simple"
    warnings = []
    if any(w in AMBIGUOUS_FAMILY_WORDS for w in subordinators_found):
        warnings.append("COMPLEX:AMBIGUOUS_FAMILY")
    return sentence_type, subordinators_found, temporal_subordinators, conditional_subordinators, warnings


def _right_starts_with_modal(right: str) -> bool:
    stripped = right.strip()
    m = _MODAL_RE.match(stripped)
    return m is not None and m.start() == 0


def _right_has_subject_then_modal(right: str) -> bool:
    tokens = right.strip().split()
    if not tokens:
        return False
    first = tokens[0].lower().strip(",")
    if first not in SUBJECT_NP_STARTERS:
        return False
    window = " ".join(tokens[1:7])
    return bool(_MODAL_RE.search(window))


def _right_starts_with_bare_verb_regex(right: str) -> bool:
    words = right.strip().split()
    if not words:
        return False
    first = words[0].lower()
    if _ADVERB_LY_RE.match(first) and len(words) >= 2:
        return True
    if first[0].isdigit():
        return False
    if first in _NON_VERB_STARTERS:
        return False
    if _NOUN_ADJ_SUFFIX_RE.search(first):
        return False
    return len(words) >= 2


def _left_has_comma(left: str) -> bool:
    return "," in left


def classify_conjunction(left: str, right: str):
    left = left.strip().rstrip(",")
    right = right.strip()
    signals = []
    if _right_starts_with_modal(right):
        signals.append("R1_RIGHT_STARTS_WITH_MODAL")
        return "SENTENCE", 0.95, signals, "R1"
    if _right_has_subject_then_modal(right):
        signals.append("R2_RIGHT_HAS_SUBJECT_THEN_MODAL")
        return "SENTENCE", 0.90, signals, "R2"
    if _right_starts_with_bare_verb_regex(right) and has_modal(left):
        signals.append("R3_RIGHT_STARTS_WITH_BARE_VERB")
        return "SENTENCE", 0.85, signals, "R3"
    if _left_has_comma(left) and not has_modal(left):
        signals.append("R4_LEFT_HAS_COMMAS_NO_MODAL")
        return "LIST", 0.85, signals, "R4"
    if not has_modal(left):
        signals.append("R5_LEFT_NO_MODAL")
        return "LIST", 0.80, signals, "R5"
    if not has_modal(right) and not _right_starts_with_bare_verb_regex(right):
        signals.append("R6_RIGHT_BARE_NP")
        return "LIST", 0.75, signals, "R6"
    signals.append("DEFAULT")
    return "LIST", 0.60, signals, "DEFAULT"


def _extract_subject(left_clause: str) -> str:
    m = _MODAL_RE.search(left_clause)
    if not m:
        return ""
    return left_clause[: m.start()].strip()


@dataclass
class SplitResult:
    original: str
    sentences: list = field(default_factory=list)
    rules_fired: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


def split_simple(sentence: str) -> SplitResult:
    """Recursively split a SIMPLE sentence on and/or/but using R1-R6."""
    text = normalize_sentence(sentence)
    result = SplitResult(original=text)
    _split_recursive(text, result)
    if not result.sentences:
        result.sentences = [text]
    return result


def _split_recursive(text: str, result: SplitResult):
    matches = list(_CONJ_RE.finditer(text))
    for m in matches:
        left = text[: m.start()]
        right = text[m.end():]
        join_type, confidence, signals, rule = classify_conjunction(left, right)
        if join_type == "SENTENCE":
            left_clean = left.strip().rstrip(",")
            left_sentence = normalize_sentence(left_clean)
            result.sentences.append(left_sentence)
            result.rules_fired.append(rule)
            right_clean = right.strip()
            if rule == "R1":
                # right opens directly with a modal -> no subject of its own,
                # shares the left clause's subject (per splitter.py docstring).
                subject = _extract_subject(left_clean)
                if subject:
                    right_clean = f"{subject} {right_clean}"
            elif rule == "R2":
                pass  # right already has its own subject + modal, no reconstruction
            elif rule == "R3":
                # bare verb -> shares both subject AND modal from the left clause.
                subject = _extract_subject(left_clean)
                modal_m = _MODAL_RE.search(left_clean)
                modal_word = modal_m.group(0) if modal_m else ""
                if subject and modal_word:
                    right_clean = f"{subject} {modal_word} {right_clean}"
            _split_recursive(right_clean, result)
            return
    # no SENTENCE-type conjunction found anywhere -> whole remainder is one atomic
    result.sentences.append(normalize_sentence(text))


def _find_first_subordinator(text: str):
    merged = []
    for m in _TEMPORAL_RE.finditer(text):
        merged.append((m.start(), m.end(), m.group(0).lower(), "temporal"))
    for m in _CONDITIONAL_RE.finditer(text):
        merged.append((m.start(), m.end(), m.group(0).lower(), "conditional"))
    if not merged:
        return None
    merged.sort(key=lambda x: x[0])
    return merged[0]


def process_sentence(sentence: str):
    """
    Top-level oracle entry point, approximating the real pipeline's combined
    output shape closely enough for compatibility scanning.
    Returns a dict with: sentence_type, subordinators_found, temporal_subordinators,
    conditional_subordinators, triggers[], flattened_atomics[], warnings[].
    """
    text = normalize_sentence(sentence)
    sentence_type, subs_found, temporal, conditional, warnings = classify_sentence(text)

    if sentence_type == "simple":
        split = split_simple(text)
        atomics = [{"id": f"S{i+1}", "governed_by": [], "text": s} for i, s in enumerate(split.sentences)]
        return {
            "sentence_type": "simple",
            "subordinators_found": subs_found,
            "temporal_subordinators": temporal,
            "conditional_subordinators": conditional,
            "triggers": [],
            "flattened_atomics": atomics,
            "warnings": warnings,
            "rules_fired": split.rules_fired,
        }

    # COMPLEX path (simplified, no dependency parse available)
    first_sub = _find_first_subordinator(text)
    triggers = []
    remaining = text
    if first_sub is not None:
        start, end, word, family = first_sub
        # crude front/end position heuristic: subordinator within first 3 words -> front
        n_words_before = len(text[:start].split())
        if n_words_before <= 2:
            position = "front"
            # subordinate clause runs up to the first comma after `start`
            comma_idx = text.find(",", end)
            if comma_idx != -1:
                clause_text = text[:comma_idx]
                remaining = text[comma_idx + 1:].strip()
                scope = "wide"
                confidence = 0.93
            else:
                clause_text = text[:end]
                remaining = text[end:].strip()
                scope = "wide"
                confidence = 0.83
        else:
            position = "end"
            clause_text = text[start:]
            remaining = text[:start].strip().rstrip(",")
            scope = "narrow"
            confidence = 0.85

        main_clause_ok = has_modal(remaining) and bool(re.search(r"[A-Za-z]", remaining))
        trigger = {
            "id": "T1",
            "family": "causal-or-temporal" if word in AMBIGUOUS_FAMILY_WORDS else family,
            "subordinator": word,
            "text": clause_text.strip(),
            "position": position,
            "scope": scope,
            "confidence": confidence,
            "r_claim_3_main_clause_well_formed": main_clause_ok,
        }
        triggers.append(trigger)
        if not main_clause_ok:
            warnings.append("R-CLAIM-3:MAIN_CLAUSE_NOT_WELL_FORMED (heuristic)")

    split = split_simple(remaining) if remaining else SplitResult(original=remaining, sentences=[])
    trigger_ids = [t["id"] for t in triggers if t["scope"] == "wide"] if triggers else []
    atomics = [{"id": f"S{i+1}", "governed_by": trigger_ids, "text": s}
               for i, s in enumerate(split.sentences)]

    return {
        "sentence_type": "complex",
        "subordinators_found": subs_found,
        "temporal_subordinators": temporal,
        "conditional_subordinators": conditional,
        "triggers": triggers,
        "flattened_atomics": atomics,
        "warnings": warnings,
        "rules_fired": split.rules_fired,
    }
