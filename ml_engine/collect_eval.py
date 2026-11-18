"""
Prepare sanitized traceback records for manual evaluation/classification labeling.

Input:
    ml_engine/data/eval/raw_tracebacks.jsonl

Outputs:
    ml_engine/data/eval/eval_to_label.csv
        Sanitized records with local-only source metadata/URLs.

    ml_engine/data/eval/eval_to_label_clean.csv
        URL-free working file for manual labeling (text,label).

    ml_engine/data/eval/eval_labeled.csv
        NOT generated or overwritten by this script. This is the final,
        manually labeled evaluation dataset. Keep it URL-free.

Important:
    - Keep raw_tracebacks.jsonl and eval_to_label.csv out of Git.
    - This script preserves existing manual labels when the same normalized
      classification text is encountered again.
    - Risk assessment fails closed: if sanitization/risk assessment fails,
      the record is skipped rather than exported.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from client.runner import parse_error
from sanitizer.sanitizer import sanitize, assess_risk


# 1. PATHS AND CONFIGURATION
SCRIPT_DIR = Path(__file__).resolve().parent
EVAL_DIR = SCRIPT_DIR / "data" / "eval"

RAW = EVAL_DIR / "raw_tracebacks.jsonl"
OUT_METADATA = EVAL_DIR / "eval_to_label.csv"
OUT_CLEAN = EVAL_DIR / "eval_to_label_clean.csv"

# Existing manually labeled files are read only for label preservation.
# This script never overwrites eval_labeled.csv.
FINAL_LABELED = EVAL_DIR / "eval_labeled.csv"

METADATA_FIELDS = [
    "text",
    "label",
    "source",
    "source_type",
    "repository_url",
    "issue_url",
    "exception_type",
    "traceback_hash",
]

CLEAN_FIELDS = ["text", "label"]


# 2. NORMALIZATION AND HASHING
def normalize_text(text: str) -> str:
    """Normalize whitespace for matching and duplicate detection."""
    return " ".join(text.split())


def text_hash(text: str) -> str:
    """Generate a stable SHA-256 hash for classification text."""
    normalized = normalize_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


# 3. LOAD EXISTING LABELS
def load_existing_labels(path: Path) -> dict[str, str]:
    """
    Load existing non-empty labels keyed by normalized classification text.

    Only text and label are needed. Extra columns in an older CSV are ignored.
    If duplicate rows have conflicting labels, keep the first non-empty label
    and report the conflict for manual review.
    """
    labels: dict[str, str] = {}

    if not path.exists():
        return labels

    conflicts = 0

    try:
        with path.open("r", newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)

            if not reader.fieldnames or not {"text", "label"}.issubset(
                set(reader.fieldnames)
            ):
                print(
                    f"[WARNING] {path.name} does not contain both "
                    "'text' and 'label' columns. Ignoring it for label recovery."
                )
                return labels

            for row_number, row in enumerate(reader, start=2):
                text = row.get("text") or ""
                label = (row.get("label") or "").strip()

                if not text.strip() or not label:
                    continue

                key = normalize_text(text)

                if key in labels and labels[key] != label:
                    conflicts += 1
                    print(
                        f"[WARNING] Conflicting labels in {path.name}, "
                        f"row {row_number}, for the same text. "
                        f"Keeping the first label: {labels[key]!r}"
                    )
                    continue

                labels[key] = label

    except (OSError, csv.Error, UnicodeError) as error:
        print(
            f"[WARNING] Could not read labels from {path}: {error}. "
            "No labels from this file will be used."
        )
        return {}

    print(f"[INFO] Recovered {len(labels)} existing label(s) from {path.name}.")
    if conflicts:
        print(f"[WARNING] Found {conflicts} conflicting label row(s).")

    return labels


def recover_labels() -> dict[str, str]:
    """
    Recover labels from existing files.

    Priority:
      1. eval_labeled.csv (final manually labeled dataset)
      2. eval_to_label_clean.csv (working labeling file)

    A label from the final file takes precedence over the working file.
    """
    recovered: dict[str, str] = {}

    for path in (OUT_CLEAN, FINAL_LABELED):
        file_labels = load_existing_labels(path)
        # Later files have higher priority.
        recovered.update(file_labels)

    return recovered


# 4. LOAD AND VALIDATE RAW JSONL
def load_raw_data(path: Path) -> tuple[list[dict[str, Any]], int]:
    """Load valid traceback records, skipping malformed JSONL lines."""
    records: list[dict[str, Any]] = []
    malformed = 0

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                print(f"[WARNING] Invalid JSON at line {line_number}.")
                continue

            if not isinstance(record, dict):
                malformed += 1
                continue

            traceback_text = record.get("traceback")

            if not isinstance(traceback_text, str) or not traceback_text.strip():
                malformed += 1
                continue

            records.append(record)

    return records, malformed


# 5. PARSE, SANITIZE, ASSESS RISK, AND DEDUPLICATE
def process_records(
    records: list[dict[str, Any]],
    existing_labels: dict[str, str],
) -> tuple[list[dict[str, str]], dict[str, int]]:
    """
    Convert raw traceback records into sanitized classification examples.

    The model-facing text is exactly:
        <parsed error type> <sanitized message>

    Labels are preserved by matching normalized classification text, never
    by row number or source URL.
    """
    rows: list[dict[str, str]] = []
    seen_text_hashes: set[str] = set()

    stats = Counter()

    for record_index, record in enumerate(records, start=1):
        stats["raw_records"] += 1
        traceback_text = record["traceback"]

        # Parse traceback.
        try:
            parsed = parse_error(traceback_text)
        except Exception as error:
            stats["parse_errors"] += 1
            print(
                f"[WARNING] Parser failed for raw record {record_index}: "
                f"{type(error).__name__}"
            )
            continue

        if (
            not isinstance(parsed, (tuple, list))
            or len(parsed) != 2
        ):
            stats["unparsable"] += 1
            continue

        error_type, message = parsed

        if (
            not isinstance(error_type, str)
            or not error_type.strip()
            or not isinstance(message, str)
            or not message.strip()
        ):
            stats["invalid_parse_output"] += 1
            continue

        # Sanitize potentially sensitive content.
        try:
            sanitized_message = sanitize(message)
        except Exception as error:
            stats["sanitizer_errors"] += 1
            print(
                f"[WARNING] Sanitizer failed for raw record {record_index}: "
                f"{type(error).__name__}"
            )
            continue

        if (
            not isinstance(sanitized_message, str)
            or not sanitized_message.strip()
        ):
            stats["invalid_sanitized_message"] += 1
            continue

        sanitized_message = sanitized_message.strip()

        # Fail closed: anything other than an explicit safe result is excluded.
        try:
            risk_result = assess_risk(sanitized_message)
        except Exception as error:
            stats["risk_assessment_errors"] += 1
            print(
                f"[WARNING] Risk assessment failed for raw record "
                f"{record_index}: {type(error).__name__}"
            )
            continue

        if risk_result == "review":
            stats["blocked_by_risk_gate"] += 1
            continue

        classification_text = f"{error_type.strip()} {sanitized_message}".strip()

        if not classification_text:
            stats["empty_text"] += 1
            continue

        normalized_text = normalize_text(classification_text)
        digest = text_hash(classification_text)

        if digest in seen_text_hashes:
            stats["duplicates"] += 1
            continue

        seen_text_hashes.add(digest)

        # Preserve a prior manual label for exactly the same normalized text.
        label = existing_labels.get(normalized_text, "")

        rows.append(
            {
                "text": classification_text,
                "label": label,
                "source": str(record.get("source") or "unknown"),
                "source_type": str(record.get("source_type") or "unknown"),
                "repository_url": str(record.get("repository_url") or ""),
                "issue_url": str(record.get("issue_url") or ""),
                "exception_type": error_type.strip(),
                "traceback_hash": str(record.get("traceback_hash") or ""),
            }
        )

        stats["kept"] += 1
        if label:
            stats["labels_preserved"] += 1

    return rows, dict(stats)


# 6. WRITE CSV SAFELY
def write_csv(
    rows: list[dict[str, str]],
    path: Path,
    fieldnames: list[str],
) -> None:
    """Write a CSV using a temporary file, then replace the destination."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")

    try:
        with temporary_path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames,
                extrasaction="ignore",
            )
            writer.writeheader()
            writer.writerows(rows)

        temporary_path.replace(path)

    except Exception:
        if temporary_path.exists():
            temporary_path.unlink()
        raise


# 7. MAIN PIPELINE
def main() -> None:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    if not RAW.exists():
        raise FileNotFoundError(
            f"Raw dataset not found: {RAW}\n"
            "Run collect_github.py first."
        )

    print("========== COLLECT EVAL ==========")
    print(f"Input: {RAW}")

    # Recover labels before writing anything.
    existing_labels = recover_labels()

    print("\nLoading raw traceback dataset...")
    records, malformed = load_raw_data(RAW)
    print(f"Valid raw records: {len(records)}")
    print(f"Malformed/invalid records: {malformed}")

    print("\nParsing, sanitizing, checking risk, and deduplicating...")
    rows, stats = process_records(records, existing_labels)

    # Full metadata file is local only because it contains source URLs.
    write_csv(rows, OUT_METADATA, METADATA_FIELDS)

    # URL-free working file for manual labeling.
    clean_rows = [
        {"text": row["text"], "label": row["label"]}
        for row in rows
    ]
    write_csv(clean_rows, OUT_CLEAN, CLEAN_FIELDS)

    # Do not create or overwrite FINAL_LABELED. It is a human-reviewed artifact.
    print("\n========== DATASET SUMMARY ==========")
    print(f"Raw valid records          : {len(records)}")
    print(f"Malformed/invalid JSONL    : {malformed}")
    print(f"Kept records               : {stats.get('kept', 0)}")
    print(f"Unparsable                 : {stats.get('unparsable', 0)}")
    print(f"Parser errors              : {stats.get('parse_errors', 0)}")
    print(f"Invalid parser output      : {stats.get('invalid_parse_output', 0)}")
    print(f"Sanitizer errors           : {stats.get('sanitizer_errors', 0)}")
    print(f"Invalid sanitized messages : {stats.get('invalid_sanitized_message', 0)}")
    print(f"Risk assessment errors     : {stats.get('risk_assessment_errors', 0)}")
    print(f"Blocked by risk gate       : {stats.get('blocked_by_risk_gate', 0)}")
    print(f"Empty classification text : {stats.get('empty_text', 0)}")
    print(f"Duplicates                 : {stats.get('duplicates', 0)}")
    print(f"Preserved manual labels    : {stats.get('labels_preserved', 0)}")

    print("\nException type distribution:")
    distribution = Counter(row["exception_type"] for row in rows)
    if distribution:
        for exception_name, count in distribution.most_common():
            print(f"  {exception_name}: {count}")
    else:
        print("  No records available.")

    print("\nLabel distribution (existing labels only):")
    label_distribution = Counter(
        row["label"] for row in clean_rows if row["label"].strip()
    )
    if label_distribution:
        for label, count in label_distribution.most_common():
            print(f"  {label}: {count}")
    else:
        print("  No manually labeled records preserved yet.")

    print("\n========== OUTPUTS ==========")
    print(f"Metadata CSV (LOCAL ONLY): {OUT_METADATA}")
    print(f"Clean labeling CSV       : {OUT_CLEAN}")
    print(f"Final labeled CSV        : {FINAL_LABELED} (not overwritten)")
    print("\nAfter manual labeling, save the completed clean CSV as:")
    print(f"  {FINAL_LABELED}")
    print("=================================")


if __name__ == "__main__":
    main()
