from fastapi import FastAPI
from pydantic import BaseModel
from local_service.explainer import EXPLANATIONS, normalize_error_type


app = FastAPI()

# Stores the most recent /analyze result so other clients (e.g. a future
# widget) can poll for it without needing the original request.
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
    """Looks up an explanation for the given error type. Falls back to a generic message for unrecognized types."""
    category = normalize_error_type(request.error_type)
    explanation = EXPLANATIONS.get(category, "An error occurred, but no specific explanation is available yet.")

    result = {
        "explanation": explanation,
        "category": category,
        "source": "rules",
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