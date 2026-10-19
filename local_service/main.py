from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from local_service.explainer import EXPLANATIONS, normalize_error_type
from local_service.classifier_service import predict as ml_predict
from local_service.settings import load_settings
from local_service.llm_adapter import explain_with_llm
from sanitizer.sanitizer import sanitize

app = FastAPI()

latest_result = {}

# Below this confidence, or for other_error, the local LLM may add a richer explanation.
LLM_CONFIDENCE_THRESHOLD = 0.7


@app.get("/")
def read_root():
    """Basic health-check route confirming the server is running."""
    return {"message": "DevMentor is running"}


class AnalyzeRequest(BaseModel):
    error_type: str
    message: str
    fingerprint: str


def _enrich_with_llm(fingerprint: str, category: str, error_type: str, message: str):
    """Runs after the response is sent. Adds an LLM explanation to the latest
    result, but only if no newer error has replaced it in the meantime."""
    global latest_result
    text = explain_with_llm(category, error_type, sanitize(message))
    if text and latest_result.get("fingerprint") == fingerprint:
        latest_result = {**latest_result, "llm_explanation": text}


@app.post("/analyze")
def analyze(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """Classifies the error with the ML model when confident, falling back to
    the rules mapping when confidence is low. Optionally upgrades the
    explanation with a local LLM for weak cases."""
    global latest_result

    settings = load_settings()
    threshold = settings.get("confidence_threshold", 0.6)

    ml_result = ml_predict(request.error_type, request.message)

    if ml_result["confidence"] >= threshold:
        category = ml_result["category"]
        source = "ml"
    else:
        category = normalize_error_type(request.error_type)
        source = "rules"

    explanation = EXPLANATIONS.get(
        category, "An error occurred, but no specific explanation is available yet."
    )

    result = {
        "explanation": explanation,
        "category": category,
        "source": source,
        "confidence": ml_result["confidence"],
        "fingerprint": request.fingerprint,
    }
    latest_result = result

    use_llm = (
        settings.get("privacy_mode") == "local_llm"
        and (category == "other_error"
             or ml_result["confidence"] < LLM_CONFIDENCE_THRESHOLD)
    )
    if use_llm:
        background_tasks.add_task(
            _enrich_with_llm, request.fingerprint, category,
            request.error_type, request.message,
        )

    return result


@app.get("/latest")
def get_latest():
    """Returns the most recent /analyze result, or a message if none exists yet."""
    if not latest_result:
        return {"message": "No errors analyzed yet."}
    return latest_result