import json
from models import AnalysisResult

EXTRACT_PROMPT = """以下の通話テキストから情報を抽出してください。
必ずJSON形式のみで回答し、他のテキストは含めないでください。

テキスト:
{text}

抽出項目:
- genre: 相談ジャンル（例: 水道, 道路, ゴミ収集, 騒音など）
- category: サブカテゴリー（例: 漏水, 陥没, 不法投棄など）
- address: 顧客の住所（不明な場合は空文字）
- consultation: 相談内容の要約（100文字以内）

回答:
{{"genre": "...", "category": "...", "address": "...", "consultation": "..."}}"""


def parse_response(raw: str) -> AnalysisResult:
    """AI レスポンスからコードブロックを除去して JSON パースする。"""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    data = json.loads(raw)
    return AnalysisResult(**data)
