from pydantic import BaseModel, field_validator


class AnalysisResult(BaseModel):
    genre: str = ""
    category: str = ""
    address: str = ""
    consultation: str = ""


class AnalyzeRequest(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def text_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be empty")
        return v
