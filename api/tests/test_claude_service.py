from unittest.mock import AsyncMock, MagicMock, patch
from services.claude import extract_fields
from models import AnalysisResult


async def test_extract_fields_parses_json_response():
    mock_content = MagicMock()
    mock_content.text = (
        '{"genre": "水道", "category": "漏水", '
        '"address": "東京都新宿区1-1", "consultation": "台所の蛇口から水が漏れている"}'
    )
    mock_message = MagicMock()
    mock_message.content = [mock_content]

    with patch("services.claude.client.messages.create", AsyncMock(return_value=mock_message)):
        result = await extract_fields("台所の蛇口から水漏れが発生しています。住所は東京都新宿区1-1です。")

    assert isinstance(result, AnalysisResult)
    assert result.genre == "水道"
    assert result.category == "漏水"
    assert result.address == "東京都新宿区1-1"
    assert result.consultation == "台所の蛇口から水が漏れている"


async def test_extract_fields_returns_empty_strings_for_missing_fields():
    mock_content = MagicMock()
    mock_content.text = (
        '{"genre": "道路", "category": "陥没", "address": "", "consultation": "道路に穴が開いている"}'
    )
    mock_message = MagicMock()
    mock_message.content = [mock_content]

    with patch("services.claude.client.messages.create", AsyncMock(return_value=mock_message)):
        result = await extract_fields("道路に穴が開いています")

    assert result.genre == "道路"
    assert result.address == ""
