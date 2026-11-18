"""Validate the labeled eval set; optionally remove rows that leak from training.

Usage:
    python ml_engine/check_eval.py            # report only
    python ml_engine/check_eval.py --clean    # backup, then drop overlap + duplicates
"""
import shutil
import sys

import pandas as pd

EVAL = "ml_engine/data/eval/eval_labeled.csv"
BACKUP = "ml_engine/data/eval/eval_labeled_backup.csv"
TRAIN = "ml_engine/data/labeled/dataset.csv"
LABELS = {
    "syntax_error", "type_error", "none_type_error", "key_error", "index_error",
    "attribute_error", "module_not_found", "file_not_found", "permission_error",
    "value_error", "network_error", "other_error",
}


def norm(s):
    return " ".join(str(s).split())


def main():
    clean = "--clean" in sys.argv
    ev = pd.read_csv(EVAL)
    tr = pd.read_csv(TRAIN)
    ev["_key"] = ev["text"].map(norm)
    train_keys = set(tr["text"].map(norm))

    print(f"Rows: {len(ev)} | unlabeled: {ev['label'].isna().sum()}")

    bad = ev[ev["label"].notna() & ~ev["label"].isin(LABELS)]
    if len(bad):
        print("\nInvalid labels (fix these by hand):")
        print(bad[["text", "label"]].to_string())

    dup_mask = ev["_key"].duplicated(keep="first")
    overlap_mask = ev["_key"].isin(train_keys)
    print(f"\nDuplicate texts (extra copies): {int(dup_mask.sum())}")
    print(f"Exact overlap with training data: {int(overlap_mask.sum())}")
    for t in ev.loc[overlap_mask, "text"].head(15):
        print("  ", t)

    if clean:
        shutil.copyfile(EVAL, BACKUP)
        kept = ev[~(dup_mask | overlap_mask)].drop(columns="_key")
        kept.to_csv(EVAL, index=False, encoding="utf-8")
        print(f"\nBackup saved to {BACKUP}")
        print(f"Removed {len(ev) - len(kept)} rows; {len(kept)} remain in {EVAL}")
        ev = kept.assign(_key=kept["text"].map(norm))

    counts = ev["label"].value_counts()
    print("\nPer-category counts:\n", counts.to_string())
    missing = LABELS - set(counts.index)
    if missing:
        print("\nCategories with no examples:", sorted(missing))
    thin = counts[counts < 8]
    if len(thin):
        print("Under 8 examples (scores unreliable):", dict(thin))
    if not clean and (overlap_mask.any() or dup_mask.any()):
        print("\nRe-run with --clean to remove leaked/duplicate rows.")


if __name__ == "__main__":
    main()