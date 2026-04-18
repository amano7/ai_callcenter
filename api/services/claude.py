import json
import anthropic
from models import AnalysisResult

client = anthropic.AsyncAnthropic()

_PROMPT = """以下の通話テキストから情報を抽出してください。
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


async def extract_fields(text: str) -> AnalysisResult:
    message = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        messages=[{"role": "user", "content": _PROMPT.format(text=text)}],
    )
    raw = message.content[0].text.strip()
    data = json.loads(raw)
    return AnalysisResult(**data)
