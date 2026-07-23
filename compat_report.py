#!/usr/bin/env python
"""
compat_report.py

Scans fw_vtol_requirements_dataset.jsonl for compatibility with the
nuclear_sentences_v2 algorithm (see nuclear_sentences_v2_ALGORITHM_SPEC.md),
using the nuclear_lite.py oracle plus a few extra regex heuristics for things
the oracle can't detect on its own (periphrastic modality, non-registry
condition phrasing, multi-sentence requirement text).

Writes: compat_report.json (per-record flags) and prints a summary table.
"""
from __future__ import annotations
import json
import re
from collections import Counter
from nuclear_lite import process_sentence, has_modal, MODAL_WORDS

PERIPHRASTIC_MODALITY_RE = re.compile(
    r"\b(is|are|was|were)\s+(required|responsible|expected|obligated|mandated)\s+to\b"
    r"|\bneeds?\s+to\b",
    re.IGNORECASE,
)
NON_REGISTRY_CONDITION_RE = re.compile(
    r"\bin\s+the\s+event\s+(that|of)\b"
    r"|\bin\s+case\s+of\b"
    r"|\bas\s+soon\s+as\b"
    r"|\bso\s+long\s+as\b"
    r"|\bas\s+long\s+as\b"
    r"|\bshould\s+\w+.*\boccur\b"
    r"|\bin\s+order\s+to\b"
    r"|\bso\s+that\b",
    re.IGNORECASE,
)


def count_sentence_periods(text: str) -> int:
    """Count '.' characters that look like sentence terminators (not decimals/abbrevs)."""
    # crude: count '. ' (period+space) followed by a capital letter, plus a trailing period.
    mid = len(re.findall(r"\.\s+[A-Z]", text))
    return mid + 1  # +1 for the final period


def main():
    records = [json.loads(l) for l in open("fw_vtol_requirements_dataset.jsonl", encoding="utf-8")]
    report = []
    flag_counts = Counter()

    for r in records:
        req = r["requirement"]
        flags = []

        n_sentences = count_sentence_periods(req)
        if n_sentences > 1:
            flags.append(f"MULTI_SENTENCE(n={n_sentences})")

        if not has_modal(req):
            flags.append("NO_CLOSED_SET_MODAL")

        periphrastic = PERIPHRASTIC_MODALITY_RE.findall(req)
        if periphrastic:
            flags.append("PERIPHRASTIC_MODALITY")

        non_registry = NON_REGISTRY_CONDITION_RE.search(req)
        if non_registry:
            flags.append(f"NON_REGISTRY_CONDITION({non_registry.group(0)!r})")

        oracle = process_sentence(req if n_sentences == 1 else req.split(". ")[0] + ".")
        gold_n = len(r["nuclear_sentences"])
        oracle_n = len(oracle["flattened_atomics"])
        if n_sentences == 1 and oracle_n != gold_n:
            flags.append(f"ATOMIC_COUNT_MISMATCH(oracle={oracle_n},gold={gold_n})")

        for f in flags:
            key = f.split("(")[0]
            flag_counts[key] += 1

        if flags:
            report.append({
                "id": r["id"],
                "bucket": r["ambiguity"]["class"],
                "num_obligations_gold": gold_n,
                "requirement": req,
                "flags": flags,
            })

    with open("compat_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Total records: {len(records)}")
    print(f"Records with >=1 flag: {len(report)}")
    print("\nFlag counts:")
    for k, v in flag_counts.most_common():
        print(f"  {k:35s} {v}")

    print("\n--- Sample flagged records (first 15) ---")
    for r in report[:15]:
        print(f"{r['id']:14s} {r['flags']}")
        print(f"   {r['requirement'][:140]}")


if __name__ == "__main__":
    main()
