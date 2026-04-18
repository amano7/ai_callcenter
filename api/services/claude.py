import anthropic
from models import AnalysisResult
from services.prompt import EXTRACT_PROMPT, parse_response

client = anthropic.AsyncAnthropic()


async def extract_fields(text: str) -> AnalysisResult:
    message = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        messages=[{"role": "user", "content": EXTRACT_PROMPT.format(text=text)}],
    )
    return parse_response(message.content[0].text)
