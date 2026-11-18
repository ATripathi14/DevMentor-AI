"""
Evaluate the saved classifier on the hand-labeled real-error dataset.

Input : ml_engine/data/eval/eval_labeled.csv  (text,label)
Model : ml_engine/models/{vectorizer,classifier}.joblib

Evaluates only. Rows that also appear in the training data are dropped
automatically, because they would inflate the score.
"""

from __future__ import annotations

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, f1_score

from local_service.explainer import normalize_error_type
from local_service.settings import load_settings

EVAL_PATH = "ml_engine/data/eval/eval_labeled.csv"
TRAIN_PATH = "ml_engine/data/labeled/dataset.csv"
VECTORIZER_PATH = "ml_engine/models/vectorizer.joblib"
CLASSIFIER_PATH = "ml_engine/models/classifier.joblib"
DEFAULT_THRESHOLD = 0.6
MIN_ROWS = 50

# Rows where the message, not just the exception name, decides the label.
AMBIGUOUS_TYPES = {"OSError", "TimeoutError", "ImportError", "RuntimeError",
                   "Exception", "AssertionError"}


def norm(s) -> str:
    return " ".join(str(s).split())


def load_eval() -> pd.DataFrame:
    df = pd.read_csv(EVAL_PATH)
    if not {"text", "label"} <= set(df.columns):
        raise ValueError(f"{EVAL_PATH} needs 'text' and 'label' columns")
    df = df.dropna(subset=["text", "label"]).copy()
    df["text"] = df["text"].astype(str).str.strip()
    df["label"] = df["label"].astype(str).str.strip()
    df = df[(df["text"] != "") & (df["label"] != "")]

    # Leakage guard: drop duplicates and anything seen in training.
    train_keys = set(pd.read_csv(TRAIN_PATH)["text"].map(norm))
    keys = df["text"].map(norm)
    n0 = len(df)
    df = df[~keys.duplicated(keep="first") & ~keys.isin(train_keys)]
    print(f"Dropped {n0 - len(df)} duplicate/training-overlap rows")

    if df.empty:
        raise ValueError("No valid labeled rows remain.")
    if len(df) < MIN_ROWS:
        print(f"[WARNING] Only {len(df)} rows; per-category metrics are unreliable.")
    return df.reset_index(drop=True)


def load_model():
    vec = joblib.load(VECTORIZER_PATH)
    clf = joblib.load(CLASSIFIER_PATH)
    if not hasattr(clf, "predict_proba"):
        raise TypeError("Classifier has no predict_proba().")
    return vec, clf


def get_threshold() -> float:
    t = float(load_settings().get("confidence_threshold", DEFAULT_THRESHOLD))
    if not 0.0 <= t <= 1.0:
        raise ValueError(f"confidence_threshold must be in [0, 1], got {t}")
    return t


def predict(df, vec, clf, threshold):
    proba = clf.predict_proba(vec.transform(df["text"]))
    ml_pred = clf.classes_[proba.argmax(axis=1)]
    conf = proba.max(axis=1)
    rules_pred = [normalize_error_type(t.split(maxsplit=1)[0]) for t in df["text"]]
    # Same fallback as /analyze: ML when confident, otherwise rules.
    e2e = [m if c >= threshold else r for m, c, r in zip(ml_pred, conf, rules_pred)]
    return ml_pred, conf, e2e


def show(y_true, pred, title):
    print(f"\n========== {title} ==========")
    print(f"Accuracy    : {accuracy_score(y_true, pred):.3f}")
    print(f"Macro F1    : {f1_score(y_true, pred, average='macro', zero_division=0):.3f}")
    print(f"Weighted F1 : {f1_score(y_true, pred, average='weighted', zero_division=0):.3f}")
    print()
    print(classification_report(y_true, pred, zero_division=0))


def main():
    print("========== REAL-WORLD EVALUATION ==========")
    df = load_eval()
    print(f"Valid labeled examples: {len(df)}")
    print(df["label"].value_counts().to_string())

    vec, clf = load_model()
    unknown = set(df["label"]) - {str(c) for c in clf.classes_}
    if unknown:
        raise ValueError(f"Labels not in the model's classes: {sorted(unknown)}")

    threshold = get_threshold()
    print(f"\nConfidence threshold: {threshold:.3f}")

    ml_pred, conf, e2e = predict(df, vec, clf, threshold)
    y = df["label"].to_numpy()

    show(y, ml_pred, "ML ONLY")
    show(y, e2e, "ML + RULES (END-TO-END)")

    # Ambiguous subset: where the message matters.
    etype = df["text"].map(lambda t: t.split(maxsplit=1)[0].split(".")[-1])
    amb = (etype.isin(AMBIGUOUS_TYPES) | (df["label"] == "other_error")
           | (df["label"] == "none_type_error")).to_numpy()
    if amb.sum():
        e2e_arr = pd.Series(e2e).to_numpy()
        print("\n========== AMBIGUOUS SUBSET (end-to-end) ==========")
        print(f"Rows     : {int(amb.sum())}")
        print(f"Accuracy : {accuracy_score(y[amb], e2e_arr[amb]):.3f}")
        print(f"Macro F1 : {f1_score(y[amb], e2e_arr[amb], average='macro', zero_division=0):.3f}")

    to_rules = int((conf < threshold).sum())
    print("\n========== ROUTING SUMMARY ==========")
    print(f"Examples evaluated    : {len(df)}")
    print(f"Routed to rules       : {to_rules} ({to_rules / len(df):.1%})")
    print(f"Handled by ML         : {len(df) - to_rules} ({1 - to_rules / len(df):.1%})")
    print("\nNote: this set is now a DEV set. Do not tune rules or the threshold on it "
          "and report the result as a test score.")


if __name__ == "__main__":
    main()