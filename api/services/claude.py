import os
import anthropic
from models import AnalysisResult
from services.prompt import EXTRACT_PROMPT, parse_response

client = anthropic.AsyncAnthropic()
_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")


async def extract_fields(text: str) -> AnalysisResult:
    message = await client.messages.create(
        model=_MODEL,
        max_tokens=256,
        messages=[{"role": "user", "content": EXTRACT_PROMPT.format(text=text)}],
    )
    return parse_response(message.content[0].text)
