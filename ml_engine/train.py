"""Standalone script to train and save the DevMentor AI error classifier.

Reproduces the pipeline built in training_and_evaluation.ipynb: 
load the labeled dataset, split it, vectorize with TF-IDF, train a 
Logistic Regression classifier, evaluate it, and save both the 
vectorizer and the trained model to disk.

Run with: python ml_engine/train.py
"""

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib


def main():
    # Load the labeled dataset
    df = pd.read_csv("ml_engine/data/labeled/dataset.csv")
    print(f"Loaded {len(df)} labeled examples across {df['label'].nunique()} categories")

    X = df["text"]
    y = df["label"]

    # Stratified split so every category is represented in both sets
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Vectorize: fit only on training data, to avoid leaking test data into the vocabulary
    vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    # Train Logistic Regression — chosen over Linear SVM based on comparison
    # in the notebook (0.86 vs 0.77 macro F1 on this dataset)
    clf = LogisticRegression(max_iter=1000)
    clf.fit(X_train_vec, y_train)

    # Evaluate
    y_pred = clf.predict(X_test_vec)
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, zero_division=0))

    # Save the vectorizer and model for use in classifier_service.py later
    joblib.dump(vectorizer, "ml_engine/models/vectorizer.joblib")
    joblib.dump(clf, "ml_engine/models/classifier.joblib")
    print("Saved vectorizer.joblib and classifier.joblib to ml_engine/models/")


if __name__ == "__main__":
    main()