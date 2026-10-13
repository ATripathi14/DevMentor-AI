import joblib
import os

_VECTORIZER_PATH = os.path.join(os.path.dirname(__file__), "..", "ml_engine", "models", "vectorizer.joblib")
_CLASSIFIER_PATH = os.path.join(os.path.dirname(__file__), "..", "ml_engine", "models", "classifier.joblib")

try:
    _vectorizer = joblib.load(_VECTORIZER_PATH)
    _classifier = joblib.load(_CLASSIFIER_PATH)
except FileNotFoundError:
    _vectorizer = None
    _classifier = None
    print("[DevMentor] Model files not found. Run: python ml_engine/train.py "
          "(falling back to rules-only mode)")


def predict(error_type: str, message: str) -> dict:
    """Classifies a sanitized error with the trained model.
    Returns {"category": str, "confidence": float}. If the model is not
    available, returns confidence 0.0 so the caller falls back to rules."""
    if _classifier is None:
        return {"category": "other_error", "confidence": 0.0}

    text = f"{error_type} {message}"
    vector = _vectorizer.transform([text])
    probabilities = _classifier.predict_proba(vector)[0]
    predicted_index = probabilities.argmax()
    return {
        "category": _classifier.classes_[predicted_index],
        "confidence": float(probabilities[predicted_index]),
    }