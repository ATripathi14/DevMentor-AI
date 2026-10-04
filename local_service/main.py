from fastapi import FastAPI
from pydantic import BaseModel
from local_service.explainer import EXPLANATIONS, normalize_error_type
from local_service.classifier_service import predict as ml_predict
from local_service.settings import load_settings


app = FastAPI()

latest_result = {}


@app.get("/")
def read_root():
    """Basic health-check route confirming the server is running."""
    return {"message": "DevMentor is running"}


class AnalyzeRequest(BaseModel):
    error_type: str
    message: str
    fingerprint: str


@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    """Classifies the error using the ML model when confident, falling back
    to the rules-based mapping when the model's confidence is too low."""
    settings = load_settings()
    threshold = settings.get("confidence_threshold", 0.6)

    ml_result = ml_predict(request.error_type, request.message)

    if ml_result["confidence"] >= threshold:
        category = ml_result["category"]
        source = "ml"
    else:
        category = normalize_error_type(request.error_type)
        source = "rules"

    explanation = EXPLANATIONS.get(category, "An error occurred, but no specific explanation is available yet.")

    result = {
        "explanation": explanation,
        "category": category,
        "source": source,
        "confidence": ml_result["confidence"],
        "fingerprint": request.fingerprint,
    }

    global latest_result
    latest_result = result

    return result


@app.get("/latest")
def get_latest():
    """Returns the most recent /analyze result, or a message if none exists yet."""
    if not latest_result:
        return {"message": "No errors analyzed yet."}
    return latest_result