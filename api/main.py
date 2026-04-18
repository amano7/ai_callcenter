import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import analyze, stream

app = FastAPI(title="AI コールセンター API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router)
app.include_router(stream.router)

# widget/ ディレクトリが存在する場合のみマウント（テスト時は不要）
if os.path.exists("widget"):
    from fastapi.staticfiles import StaticFiles

    app.mount("/ai-callcenter", StaticFiles(directory="widget"), name="widget")
