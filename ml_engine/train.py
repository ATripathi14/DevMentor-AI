"""Standalone script to train and save the DevMentor AI error classifier.

Reproduces the pipeline built in training_and_evaluation.ipynb: 
load the labeled dataset, split it, vectorize with TF-IDF, train a 
calibrated Linear SVM classifier, evaluate it, and save both the 
vectorizer and the trained model to disk.

Run with: python ml_engine/train.py
"""

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib


def main():
    df = pd.read_csv("ml_engine/data/labeled/dataset.csv")
    print(f"Loaded {len(df)} labeled examples across {df['label'].nunique()} categories")

    X = df["text"]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    # Calibrated Linear SVM — chosen over Logistic Regression after the
    # dataset expansion showed a wide performance gap (0.957 vs 0.801
    # macro F1, 3-fold CV). Calibration costs ~2.6 points of macro F1
    # but is required to expose predict_proba for confidence-threshold
    # routing. cv=2 is used for calibration's internal split since
    # several classes (index_error, permission_error) have only 3 total
    # examples and can't support a nested 3-fold split.
    clf = CalibratedClassifierCV(LinearSVC(max_iter=2000), cv=2)
    clf.fit(X_train_vec, y_train)

    y_pred = clf.predict(X_test_vec)
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, zero_division=0))

    joblib.dump(vectorizer, "ml_engine/models/vectorizer.joblib")
    joblib.dump(clf, "ml_engine/models/classifier.joblib")
    print("Saved vectorizer.joblib and classifier.joblib to ml_engine/models/")


if __name__ == "__main__":
    main()