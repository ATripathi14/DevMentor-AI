from fastapi.testclient import TestClient
from local_service.main import app

client = TestClient(app)


def test_analyze_returns_correct_explanation_for_known_type():
    """A known error type should return its specific category and explanation."""
    response = client.post("/analyze", json={
        "error_type": "KeyError",
        "message": "'user_id'",
        "fingerprint": "abc123",
    })
    data = response.json()

    assert response.status_code == 200
    assert data["category"] == "key_error"
    assert "dictionary" in data["explanation"]


def test_analyze_falls_back_for_unknown_type():
    """An unrecognized error type should fall back to other_error, not crash."""
    response = client.post("/analyze", json={
        "error_type": "SomeMadeUpError",
        "message": "nonsense",
        "fingerprint": "def456",
    })
    data = response.json()

    assert response.status_code == 200
    assert data["category"] == "other_error"


def test_latest_updates_after_analyze():
    """/latest should reflect the most recent /analyze result."""
    client.post("/analyze", json={
        "error_type": "IndexError",
        "message": "list index out of range",
        "fingerprint": "ghi789",
    })
    response = client.get("/latest")
    data = response.json()

    assert data["category"] == "index_error"


def test_analyze_rejects_malformed_request():
    """Missing required fields should return a 422 validation error, not crash."""
    response = client.post("/analyze", json={
        "error_type": "KeyError",
        # missing "message" and "fingerprint"
    })

    assert response.status_code == 422