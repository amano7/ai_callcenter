from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from main import app
from models import AnalysisResult

client = TestClient(app)


def test_analyze_returns_extracted_fields():
    mock_result = AnalysisResult(
        genre="水道",
        category="漏水",
        address="東京都新宿区1-1",
        consultation="台所の蛇口から水が漏れている",
    )
    with patch("routers.analyze.extract_fields", AsyncMock(return_value=mock_result)):
        response = client.post("/analyze", json={"text": "台所の蛇口から水漏れ"})

    assert response.status_code == 200
    data = response.json()
    assert data["genre"] == "水道"
    assert data["category"] == "漏水"
    assert data["address"] == "東京都新宿区1-1"
    assert data["consultation"] == "台所の蛇口から水が漏れている"


def test_analyze_rejects_missing_text():
    response = client.post("/analyze", json={})
    assert response.status_code == 422


def test_analyze_rejects_empty_text():
    response = client.post("/analyze", json={"text": ""})
    assert response.status_code == 422
