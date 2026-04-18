import os
import google.generativeai as genai
from models import AnalysisResult
from services.prompt import EXTRACT_PROMPT, parse_response

genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))

_model = genai.GenerativeModel("gemini-2.5-flash")


async def extract_fields(text: str) -> AnalysisResult:
    response = await _model.generate_content_async(EXTRACT_PROMPT.format(text=text))
    return parse_response(response.text)
