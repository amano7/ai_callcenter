import os

_PROVIDER = os.environ.get("AI_PROVIDER", "claude").lower()

if _PROVIDER == "gemini":
    from services.gemini import extract_fields
else:
    from services.claude import extract_fields

__all__ = ["extract_fields"]
