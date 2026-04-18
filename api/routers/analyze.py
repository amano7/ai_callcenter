from fastapi import APIRouter
from models import AnalyzeRequest, AnalysisResult
from services.claude import extract_fields

router = APIRouter()


@router.post("/analyze", response_model=AnalysisResult)
async def analyze(request: AnalyzeRequest) -> AnalysisResult:
    return await extract_fields(request.text)
