#!/usr/bin/env python3
"""Bounded structural QA for one frozen Stacks TeX source/locale target pair."""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path


def strip_comments(text: str) -> str:
    out: list[str] = []
    for line in text.splitlines(keepends=True):
        cut = len(line)
        for i, char in enumerate(line):
            if char != "%":
                continue
            backslashes = 0
            j = i - 1
            while j >= 0 and line[j] == "\\":
                backslashes += 1
                j -= 1
            if backslashes % 2 == 0:
                cut = i
                break
        suffix = "\n" if line.endswith("\n") else ""
        out.append(line[:cut].rstrip("\r\n") + suffix)
    return "".join(out)


def sequence(text: str, pattern: str) -> list[str]:
    return [m.group(1) for m in re.finditer(pattern, text, re.DOTALL)]


def first_mismatch(left: list[str], right: list[str]) -> dict | None:
    limit = min(len(left), len(right))
    for index in range(limit):
        if left[index] != right[index]:
            return {"index": index, "source": left[index], "target": right[index]}
    if len(left) != len(right):
        return {
            "index": limit,
            "source": left[limit] if limit < len(left) else None,
            "target": right[limit] if limit < len(right) else None,
        }
    return None


def sections(text: str) -> list[tuple[str, str]]:
    starts = list(re.finditer(r"\\section\{.*?\}\s*\\label\{([^}]*)\}", text, re.DOTALL))
    result: list[tuple[str, str]] = []
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        result.append((match.group(1), text[match.end() : end]))
    return result


def inline_math_multiset(text: str) -> collections.Counter[str]:
    values: list[str] = []
    start: int | None = None
    i = 0
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == "$":
            if i + 1 < len(text) and text[i + 1] == "$":
                i += 2
                continue
            if start is None:
                start = i + 1
            else:
                values.append(re.sub(r"\s+", "", text[start:i]))
                start = None
        i += 1
    if start is not None:
        values.append("__UNBALANCED_INLINE_MATH__")
    return collections.Counter(values)


def residual_english_candidates(text: str) -> list[dict]:
    allowed = {
        "ad", "Artin", "Aut", "BG", "Cech", "Chow", "Cohen", "Cox", "DM",
        "étale", "etale", "faithfully", "finite", "fppf", "fpqc", "Gerbe",
        "Hilbert", "inertia", "Isom", "Picard", "principal", "Quot", "scheme",
        "Sch", "smooth", "Stacks", "stack", "torsor", "Torsors", "Yoneda",
    }
    candidates: list[dict] = []
    cleaned = strip_comments(text)

    def preserve_newlines(match: re.Match[str]) -> str:
        return "\n" * match.group(0).count("\n")

    cleaned = re.sub(
        r"\$\$.*?\$\$|\\\[.*?\\\]|"
        r"\\begin\{(?:equation\*?|align\*?|displaymath|multline\*?)\}.*?"
        r"\\end\{(?:equation\*?|align\*?|displaymath|multline\*?)\}",
        preserve_newlines,
        cleaned,
        flags=re.DOTALL,
    )
    cleaned = re.sub(r"(?<!\\)\$(?!\$).*?(?<!\\)\$", " ", cleaned, flags=re.DOTALL)

    for line_no, raw in enumerate(cleaned.splitlines(), 1):
        line = re.sub(
            r"\\(?:label|ref|eqref|cite|input|bibliography|bibliographystyle|url|begin|end)"
            r"\{[^{}]*\}",
            " ",
            raw,
        )
        line = re.sub(r"\\[A-Za-z@]+\*?", " ", line)
        prose = line
        prose = re.sub(r"\b(?:section|lemma|proposition|theorem|definition|example|remark|proof|item|begin|end|label|ref|eqref|cite|input|bibliography|bibliographystyle|title)\b", " ", prose)
        prose = re.sub(r"[{}\[\]_^\\:/=<>0-9.,;()'\"`~-]+", " ", prose)
        words = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]{2,}", prose)
        suspicious = [word for word in words if word not in allowed]
        if suspicious:
            candidates.append({"line": line_no, "words": suspicious, "text": raw.strip()})
    return candidates


def analyze(path: Path) -> tuple[str, dict]:
    raw = path.read_text(encoding="utf-8")
    text = strip_comments(raw)
    return text, {
        "bytes": path.stat().st_size,
        "physical_lines": len(raw.splitlines()),
        "labels": len(sequence(text, r"\\label\{([^}]*)\}")),
        "refs_eqrefs": len(sequence(text, r"\\(?:ref|eqref)\{([^}]*)\}")),
        "cites": len(sequence(text, r"\\cite\{([^}]*)\}")),
        "begins": len(sequence(text, r"\\begin\{([^}]*)\}")),
        "ends": len(sequence(text, r"\\end\{([^}]*)\}")),
        "items": len(re.findall(r"\\item\b", text)),
        "xymatrix": len(re.findall(r"\\xymatrix\b", text)),
        "display_delimiters": (
            len(re.findall(r"(?<!\\)\$\$", text))
            + len(re.findall(r"\\\[|\\\]", text))
        ),
        "open_braces": len(re.findall(r"(?<!\\)\{", text)),
        "close_braces": len(re.findall(r"(?<!\\)\}", text)),
        "unescaped_dollars": len(re.findall(r"(?<!\\)\$", text)),
        "sections": len(sections(text)),
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()

    source, source_stats = analyze(args.source)
    target, target_stats = analyze(args.target)

    patterns = {
        "labels": r"\\label\{([^}]*)\}",
        "refs_eqrefs": r"\\(?:ref|eqref)\{([^}]*)\}",
        "cites": r"\\cite\{([^}]*)\}",
        "begins": r"\\begin\{([^}]*)\}",
        "ends": r"\\end\{([^}]*)\}",
    }
    ordered = {}
    for name, pattern in patterns.items():
        left = sequence(source, pattern)
        right = sequence(target, pattern)
        mismatch = first_mismatch(left, right)
        ordered[name] = {
            "equal": mismatch is None,
            "source_count": len(left),
            "target_count": len(right),
            "first_mismatch": mismatch,
        }

    source_sections = sections(source)
    target_sections = sections(target)
    section_label_mismatch = first_mismatch(
        [label for label, _ in source_sections], [label for label, _ in target_sections]
    )
    math = []
    for index in range(min(len(source_sections), len(target_sections))):
        source_label, source_body = source_sections[index]
        target_label, target_body = target_sections[index]
        source_math = inline_math_multiset(source_body)
        target_math = inline_math_multiset(target_body)
        missing = list((source_math - target_math).elements())
        extra = list((target_math - source_math).elements())
        math.append({
            "source_label": source_label,
            "target_label": target_label,
            "equal": not missing and not extra,
            "missing": missing[:20],
            "extra": extra[:20],
        })

    equal_count_names = ["items", "xymatrix", "display_delimiters"]
    counts_equal = {
        name: source_stats[name] == target_stats[name] for name in equal_count_names
    }
    result = {
        "source": str(args.source),
        "target": str(args.target),
        "source_stats": source_stats,
        "target_stats": target_stats,
        "ordered_sequences": ordered,
        "equal_counts": counts_equal,
        "section_labels_equal": section_label_mismatch is None,
        "section_label_first_mismatch": section_label_mismatch,
        "inline_math_sections": math,
        "inline_math_all_sections_equal": (
            len(source_sections) == len(target_sections)
            and all(entry["equal"] for entry in math)
        ),
        "target_balanced": {
            "braces": target_stats["open_braces"] == target_stats["close_braces"],
            "inline_dollars": target_stats["unescaped_dollars"] % 2 == 0,
            "environments": target_stats["begins"] == target_stats["ends"],
        },
        "residual_english_candidates": residual_english_candidates(target),
    }
    result["pass"] = (
        all(entry["equal"] for entry in ordered.values())
        and all(counts_equal.values())
        and result["section_labels_equal"]
        and result["inline_math_all_sections_equal"]
        and all(result["target_balanced"].values())
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
