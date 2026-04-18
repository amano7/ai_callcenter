import pytest
from pydantic import ValidationError
from models import AnalysisResult, AnalyzeRequest


def test_analysis_result_defaults_to_empty_strings():
    result = AnalysisResult()
    assert result.genre == ""
    assert result.category == ""
    assert result.address == ""
    assert result.consultation == ""


def test_analysis_result_accepts_all_fields():
    result = AnalysisResult(
        genre="水道",
        category="漏水",
        address="東京都新宿区1-1",
        consultation="台所の蛇口から水が漏れている",
    )
    assert result.genre == "水道"
    assert result.address == "東京都新宿区1-1"


def test_analyze_request_rejects_empty_text():
    with pytest.raises(ValidationError):
        AnalyzeRequest(text="")


def test_analyze_request_rejects_whitespace_only():
    with pytest.raises(ValidationError):
        AnalyzeRequest(text="   ")


def test_analyze_request_accepts_valid_text():
    req = AnalyzeRequest(text="水道から水が漏れています")
    assert req.text == "水道から水が漏れています"
