from fastapi.testclient import TestClient
from local_service.main import app
from local_service import main

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


def test_high_confidence_uses_ml(monkeypatch):
    monkeypatch.setattr(main, "ml_predict",
                        lambda t, m: {"category": "key_error", "confidence": 0.9})
    r = client.post("/analyze", json={
        "error_type": "KeyError", "message": "'x'", "fingerprint": "r1"})
    data = r.json()
    assert data["source"] == "ml"
    assert data["category"] == "key_error"


def test_low_confidence_falls_back_to_rules(monkeypatch):
    monkeypatch.setattr(main, "ml_predict",
                        lambda t, m: {"category": "other_error", "confidence": 0.2})
    r = client.post("/analyze", json={
        "error_type": "KeyError", "message": "'x'", "fingerprint": "r2"})
    data = r.json()
    assert data["source"] == "rules"
    assert data["category"] == "key_error"