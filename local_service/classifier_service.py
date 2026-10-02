import joblib
import os

_VECTORIZER_PATH = os.path.join(os.path.dirname(__file__), "..", "ml_engine", "models", "vectorizer.joblib")
_CLASSIFIER_PATH = os.path.join(os.path.dirname(__file__), "..", "ml_engine", "models", "classifier.joblib")

# Loaded once at module import time, not per-request, so inference stays fast.
_vectorizer = joblib.load(_VECTORIZER_PATH)
_classifier = joblib.load(_CLASSIFIER_PATH)


def predict(error_type: str, message: str) -> dict:
    """Classifies a sanitized error using the trained ML model.
    Returns {"category": str, "confidence": float}.
    Input text matches training format: "{error_type} {message}".
    """
    text = f"{error_type} {message}"
    vector = _vectorizer.transform([text])

    probabilities = _classifier.predict_proba(vector)[0]
    predicted_index = probabilities.argmax()

    category = _classifier.classes_[predicted_index]
    confidence = float(probabilities[predicted_index])

    return {"category": category, "confidence": confidence}