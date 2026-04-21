import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import whisper

from routers import analyze, stream

app = FastAPI()

# Whisper モデルグローバル変数
_whisper_model = None

@app.on_event("startup")
async def startup_event():
    """FastAPI 起動時に Whisper モデルをロード"""
    global _whisper_model
    if os.environ.get("USE_LOCAL_WHISPER") == "true":
        print("[app] Loading Whisper medium model...", flush=True)
        _whisper_model = whisper.load_model("medium")
        print("[app] Whisper model loaded successfully", flush=True)

@app.on_event("shutdown")
async def shutdown_event():
    """FastAPI シャットダウン時にモデルをアンロード"""
    global _whisper_model
    _whisper_model = None
    print("[app] Whisper model unloaded", flush=True)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 既存ルータ登録
app.include_router(analyze.router)
app.include_router(stream.router)

# JS ウィジェット・テストページ配信
app.mount("/ai-callcenter", StaticFiles(directory="widget", html=True), name="widget")
