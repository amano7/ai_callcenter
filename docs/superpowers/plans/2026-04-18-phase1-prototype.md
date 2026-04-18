# AI コールセンター Phase 1 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ブラウザマイク入力 → Google STT リアルタイム文字起こし → Claude API 構造化抽出 → JS ウィジェットでフォーム自動入力のプロトタイプを Docker Compose でローカル動作させる。

**Architecture:** Python FastAPI が WebSocket でブラウザから 16kHz LINEAR16 PCM 音声チャンクを受信し、Google Cloud STT でストリーミング文字起こし。200文字 or 30秒バッファ後に Claude API で `{genre, category, address, consultation}` を抽出し、WebSocket でブラウザへ push。Vanilla JS ウィジェットが `data-ai-target` 属性でフォーム入力欄に自動入力する。`GOOGLE_APPLICATION_CREDENTIALS` 未設定時はモック STT で動作し、API キーなしでもテスト可能。

**Tech Stack:** Python 3.12, FastAPI, google-cloud-speech, anthropic SDK (claude-sonnet-4-6), WebSocket, Vanilla JS (AudioWorklet), Docker Compose, pytest + pytest-asyncio

---

## File Map

| ファイル                           | 役割                                                    |
| ---------------------------------- | ------------------------------------------------------- |
| `docker-compose.yml`               | api サービス定義                                        |
| `.env.example`                     | 環境変数テンプレート                                    |
| `api/Dockerfile`                   | Python 3.12-slim イメージ                               |
| `api/requirements.txt`             | 依存ライブラリ                                          |
| `api/pytest.ini`                   | pytest 設定（asyncio_mode=auto）                        |
| `api/main.py`                      | FastAPI エントリポイント（CORS, routers, static files） |
| `api/models.py`                    | Pydantic: AnalysisResult, AnalyzeRequest                |
| `api/routers/__init__.py`          | 空ファイル                                              |
| `api/routers/analyze.py`           | POST /analyze                                           |
| `api/routers/stream.py`            | WS /stream/{session_id}                                 |
| `api/services/__init__.py`         | 空ファイル                                              |
| `api/services/claude.py`           | Claude API 構造化抽出（AsyncAnthropic）                 |
| `api/services/stt.py`              | Google STT ストリーミング（モックモード付き）           |
| `api/tests/__init__.py`            | 空ファイル                                              |
| `api/tests/conftest.py`            | pytest fixtures                                         |
| `api/tests/test_claude_service.py` | Claude service ユニットテスト                           |
| `api/tests/test_analyze.py`        | /analyze エンドポイントテスト                           |
| `api/tests/test_stream.py`         | WebSocket 接続テスト                                    |
| `widget/widget.js`                 | JS ウィジェット本体（AudioWorklet + WebSocket）         |
| `widget/audio-processor.js`        | AudioWorkletProcessor（Float32 → Int16 変換）           |
| `widget/test.html`                 | 動作確認用テストページ（モックフォーム付き）            |

---

## Task 1: Docker & プロジェクト Scaffold

**Files:**

- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `api/Dockerfile`
- Create: `api/requirements.txt`
- Create: `api/pytest.ini`
- Create: `api/routers/__init__.py`
- Create: `api/services/__init__.py`
- Create: `api/tests/__init__.py`

---

- [ ] **Step 1: `docker-compose.yml` を作成する**

```yaml
services:
  api:
    build: ./api
    ports:
      - "8000:8000"
    volumes:
      - ./api:/app
      - ./widget:/app/widget
    env_file:
      - .env
    environment:
      - PYTHONPATH=/app
```

- [ ] **Step 2: `.env.example` を作成する**

```
ANTHROPIC_API_KEY=your-anthropic-api-key-here
# Google STT を使う場合: JSON キーファイルのコンテナ内パス
# GOOGLE_APPLICATION_CREDENTIALS=/app/google-credentials.json
# 未設定の場合はモック STT が自動で有効になる
```

- [ ] **Step 3: `api/Dockerfile` を作成する**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

- [ ] **Step 4: `api/requirements.txt` を作成する**

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
anthropic==0.40.0
google-cloud-speech==2.27.0
pydantic==2.9.0
websockets==13.0
pytest==8.3.0
pytest-asyncio==0.24.0
httpx==0.27.0
```

- [ ] **Step 5: `api/pytest.ini` を作成する**

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

- [ ] **Step 6: `api/routers/__init__.py`、`api/services/__init__.py`、`api/tests/__init__.py` を空ファイルとして作成する**

各ファイルの内容: （空）

- [ ] **Step 7: Docker イメージをビルドして成功することを確認する**

```bash
cd /Users/amano7/docker/pecos/ai_callcenter
docker compose build
```

Expected: `Successfully built` で終了。エラーがないこと。

- [ ] **Step 8: コミット**

```bash
git init
git add docker-compose.yml .env.example api/
git commit -m "chore: scaffold Docker project structure"
```

---

## Task 2: Pydantic モデル

**Files:**

- Create: `api/models.py`
- Create: `api/tests/test_models.py`

---

- [ ] **Step 1: テストを書く**

`api/tests/test_models.py`:

```python
import pytest
from pydantic import ValidationError
from models import AnalysisResult, AnalyzeRequest


def test_analysis_result_defaults_to_empty_strings():
    result = AnalysisResult()
    assert result.genre == ""
    assert result.category == ""
    assert result.address == ""
    assert result.consultation == ""


def test_analysis_result_accepts_all_fields():
    result = AnalysisResult(
        genre="水道",
        category="漏水",
        address="東京都新宿区1-1",
        consultation="台所の蛇口から水が漏れている",
    )
    assert result.genre == "水道"
    assert result.address == "東京都新宿区1-1"


def test_analyze_request_rejects_empty_text():
    with pytest.raises(ValidationError):
        AnalyzeRequest(text="")


def test_analyze_request_rejects_whitespace_only():
    with pytest.raises(ValidationError):
        AnalyzeRequest(text="   ")


def test_analyze_request_accepts_valid_text():
    req = AnalyzeRequest(text="水道から水が漏れています")
    assert req.text == "水道から水が漏れています"
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
docker compose run --rm api pytest tests/test_models.py -v
```

Expected: `ModuleNotFoundError: No module named 'models'`

- [ ] **Step 3: `api/models.py` を実装する**

```python
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
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
docker compose run --rm api pytest tests/test_models.py -v
```

Expected: `5 passed`

- [ ] **Step 5: コミット**

```bash
git add api/models.py api/tests/test_models.py
git commit -m "feat: add Pydantic models for AnalysisResult and AnalyzeRequest"
```

---

## Task 3: Claude Service

**Files:**

- Create: `api/services/claude.py`
- Create: `api/tests/test_claude_service.py`

---

- [ ] **Step 1: テストを書く**

`api/tests/test_claude_service.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from services.claude import extract_fields
from models import AnalysisResult


async def test_extract_fields_parses_json_response():
    mock_content = MagicMock()
    mock_content.text = (
        '{"genre": "水道", "category": "漏水", '
        '"address": "東京都新宿区1-1", "consultation": "台所の蛇口から水が漏れている"}'
    )
    mock_message = MagicMock()
    mock_message.content = [mock_content]

    with patch("services.claude.client.messages.create", AsyncMock(return_value=mock_message)):
        result = await extract_fields("台所の蛇口から水漏れが発生しています。住所は東京都新宿区1-1です。")

    assert isinstance(result, AnalysisResult)
    assert result.genre == "水道"
    assert result.category == "漏水"
    assert result.address == "東京都新宿区1-1"
    assert result.consultation == "台所の蛇口から水が漏れている"


async def test_extract_fields_returns_empty_strings_for_missing_fields():
    mock_content = MagicMock()
    mock_content.text = (
        '{"genre": "道路", "category": "陥没", "address": "", "consultation": "道路に穴が開いている"}'
    )
    mock_message = MagicMock()
    mock_message.content = [mock_content]

    with patch("services.claude.client.messages.create", AsyncMock(return_value=mock_message)):
        result = await extract_fields("道路に穴が開いています")

    assert result.genre == "道路"
    assert result.address == ""
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
docker compose run --rm api pytest tests/test_claude_service.py -v
```

Expected: `ModuleNotFoundError: No module named 'services.claude'`

- [ ] **Step 3: `api/services/claude.py` を実装する**

```python
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
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
docker compose run --rm api pytest tests/test_claude_service.py -v
```

Expected: `2 passed`

- [ ] **Step 5: コミット**

```bash
git add api/services/claude.py api/tests/test_claude_service.py
git commit -m "feat: add Claude API service for structured field extraction"
```

---

## Task 4: POST /analyze エンドポイント

**Files:**

- Create: `api/routers/analyze.py`
- Create: `api/main.py`（最小構成 — Task 7 で完成させる）
- Create: `api/tests/test_analyze.py`

---

- [ ] **Step 1: テストを書く**

`api/tests/test_analyze.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from main import app
from models import AnalysisResult

client = TestClient(app)


def test_analyze_returns_extracted_fields():
    mock_result = AnalysisResult(
        genre="水道",
        category="漏水",
        address="東京都新宿区1-1",
        consultation="台所の蛇口から水が漏れている",
    )
    with patch("routers.analyze.extract_fields", AsyncMock(return_value=mock_result)):
        response = client.post("/analyze", json={"text": "台所の蛇口から水漏れ"})

    assert response.status_code == 200
    data = response.json()
    assert data["genre"] == "水道"
    assert data["category"] == "漏水"
    assert data["address"] == "東京都新宿区1-1"
    assert data["consultation"] == "台所の蛇口から水が漏れている"


def test_analyze_rejects_missing_text():
    response = client.post("/analyze", json={})
    assert response.status_code == 422


def test_analyze_rejects_empty_text():
    response = client.post("/analyze", json={"text": ""})
    assert response.status_code == 422
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
docker compose run --rm api pytest tests/test_analyze.py -v
```

Expected: `ModuleNotFoundError: No module named 'main'`

- [ ] **Step 3: `api/routers/analyze.py` を実装する**

```python
from fastapi import APIRouter
from models import AnalyzeRequest, AnalysisResult
from services.claude import extract_fields

router = APIRouter()


@router.post("/analyze", response_model=AnalysisResult)
async def analyze(request: AnalyzeRequest) -> AnalysisResult:
    return await extract_fields(request.text)
```

- [ ] **Step 4: `api/main.py` を最小構成で作成する（Task 7 で完成させる）**

```python
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
```

- [ ] **Step 5: テストが通ることを確認する**

```bash
docker compose run --rm api pytest tests/test_analyze.py -v
```

Expected: `3 passed`

- [ ] **Step 6: コミット**

```bash
git add api/routers/analyze.py api/main.py api/tests/test_analyze.py
git commit -m "feat: add POST /analyze endpoint"
```

---

## Task 5: STT Service

**Files:**

- Create: `api/services/stt.py`
- Create: `api/tests/test_stt_service.py`

---

- [ ] **Step 1: テストを書く**

`api/tests/test_stt_service.py`:

```python
import asyncio
import pytest
from services.stt import create_stt_session


async def test_mock_stt_returns_transcript_on_audio_chunk():
    """GOOGLE_APPLICATION_CREDENTIALS 未設定時はモック STT が動作する。"""
    audio_queue: asyncio.Queue = asyncio.Queue()
    transcript_queue: asyncio.Queue = asyncio.Queue()

    # 音声チャンクを1つ入れてから None（終了シグナル）を入れる
    await audio_queue.put(b"\x00" * 1024)
    await audio_queue.put(None)

    await create_stt_session(audio_queue, transcript_queue)

    transcript, is_final = await transcript_queue.get()
    assert isinstance(transcript, str)
    assert len(transcript) > 0
    assert is_final is True

    # 最後は (None, None) センチネルが来るはず
    sentinel = await transcript_queue.get()
    assert sentinel == (None, None)


async def test_mock_stt_sends_sentinel_on_empty_queue():
    """音声なしで None を送ってもセンチネルが届く。"""
    audio_queue: asyncio.Queue = asyncio.Queue()
    transcript_queue: asyncio.Queue = asyncio.Queue()

    await audio_queue.put(None)

    await create_stt_session(audio_queue, transcript_queue)

    sentinel = await transcript_queue.get()
    assert sentinel == (None, None)
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
docker compose run --rm api pytest tests/test_stt_service.py -v
```

Expected: `ModuleNotFoundError: No module named 'services.stt'`

- [ ] **Step 3: `api/services/stt.py` を実装する**

```python
import asyncio
import os

_MOCK_TRANSCRIPT = (
    "本日は東京都新宿区1-1-1にお住まいの田中様からお電話いただきました。"
    "台所の蛇口から水漏れが発生しているとのことです。"
    "至急修理の手配をお願いしたいとのことです。"
)


async def create_stt_session(
    audio_queue: asyncio.Queue,
    transcript_queue: asyncio.Queue,
) -> None:
    """STT セッション。GOOGLE_APPLICATION_CREDENTIALS 未設定時はモック動作。"""
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        await _mock_stt(audio_queue, transcript_queue)
    else:
        await _google_stt(audio_queue, transcript_queue)


async def _mock_stt(
    audio_queue: asyncio.Queue,
    transcript_queue: asyncio.Queue,
) -> None:
    """モック STT: 最初の音声チャンク受信後にモック文字起こしを返す。"""
    while True:
        chunk = await audio_queue.get()
        if chunk is None:
            break
        # 最初の実音声チャンクでモック文字起こしを送信
        await transcript_queue.put((_MOCK_TRANSCRIPT, True))
        # 残りのチャンクを消費する
        while True:
            remaining = await audio_queue.get()
            if remaining is None:
                break
        break
    await transcript_queue.put((None, None))


async def _google_stt(
    audio_queue: asyncio.Queue,
    transcript_queue: asyncio.Queue,
) -> None:
    """Google Cloud STT ストリーミング（スレッドプールで実行）。"""
    from google.cloud import speech  # type: ignore

    loop = asyncio.get_event_loop()

    def audio_generator():
        while True:
            future = asyncio.run_coroutine_threadsafe(audio_queue.get(), loop)
            chunk = future.result()
            if chunk is None:
                break
            yield chunk

    def run_stt() -> None:
        client = speech.SpeechClient()
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="ja-JP",
        )
        streaming_config = speech.StreamingRecognitionConfig(
            config=config,
            interim_results=True,
        )
        requests = (
            speech.StreamingRecognizeRequest(audio_content=chunk)
            for chunk in audio_generator()
        )
        responses = client.streaming_recognize(streaming_config, requests)
        for response in responses:
            for result in response.results:
                transcript = result.alternatives[0].transcript
                is_final = result.is_final
                asyncio.run_coroutine_threadsafe(
                    transcript_queue.put((transcript, is_final)), loop
                )

    await loop.run_in_executor(None, run_stt)
    await transcript_queue.put((None, None))
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
docker compose run --rm api pytest tests/test_stt_service.py -v
```

Expected: `2 passed`

- [ ] **Step 5: コミット**

```bash
git add api/services/stt.py api/tests/test_stt_service.py
git commit -m "feat: add STT service with mock mode and Google Cloud STT"
```

---

## Task 6: WebSocket /stream エンドポイント

**Files:**

- Create: `api/routers/stream.py`
- Create: `api/tests/test_stream.py`

---

- [ ] **Step 1: テストを書く**

`api/tests/test_stream.py`:

```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_websocket_accepts_connection_and_sends_connected():
    with client.websocket_connect("/stream/test-session-123") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "connected"
        assert msg["session_id"] == "test-session-123"
```

- [ ] **Step 2: テストが失敗することを確認する**

```bash
docker compose run --rm api pytest tests/test_stream.py -v
```

Expected: `ModuleNotFoundError: No module named 'routers.stream'` または接続エラー

- [ ] **Step 3: `api/routers/stream.py` を実装する**

```python
import asyncio
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from models import AnalysisResult
from services.claude import extract_fields
from services.stt import create_stt_session

router = APIRouter()

_BUFFER_MAX_CHARS = 200
_BUFFER_MAX_SECONDS = 30


@router.websocket("/stream/{session_id}")
async def websocket_stream(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    await websocket.send_json({"type": "connected", "session_id": session_id})

    audio_queue: asyncio.Queue = asyncio.Queue()
    transcript_queue: asyncio.Queue = asyncio.Queue()
    transcript_buffer = ""
    last_flush_time = time.monotonic()

    async def receive_audio() -> None:
        try:
            while True:
                data = await websocket.receive_bytes()
                await audio_queue.put(data)
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            await audio_queue.put(None)

    async def handle_transcripts() -> None:
        nonlocal transcript_buffer, last_flush_time
        while True:
            transcript, is_final = await transcript_queue.get()
            if transcript is None:
                break
            try:
                await websocket.send_json({
                    "type": "transcript",
                    "text": transcript,
                    "is_final": is_final,
                })
            except RuntimeError:
                break
            if not is_final:
                continue
            transcript_buffer += transcript + " "
            elapsed = time.monotonic() - last_flush_time
            if len(transcript_buffer) < _BUFFER_MAX_CHARS and elapsed < _BUFFER_MAX_SECONDS:
                continue
            text = transcript_buffer.strip()
            transcript_buffer = ""
            last_flush_time = time.monotonic()
            try:
                analysis = await extract_fields(text)
                await websocket.send_json({
                    "type": "analysis",
                    "analysis": analysis.model_dump(),
                })
            except Exception as e:
                try:
                    await websocket.send_json({"type": "error", "message": str(e)})
                except RuntimeError:
                    break

    await asyncio.gather(
        receive_audio(),
        create_stt_session(audio_queue, transcript_queue),
        handle_transcripts(),
    )
```

- [ ] **Step 4: テストが通ることを確認する**

```bash
docker compose run --rm api pytest tests/test_stream.py -v
```

Expected: `1 passed`

- [ ] **Step 5: 全テストが通ることを確認する**

```bash
docker compose run --rm api pytest -v
```

Expected: `9 passed`（Task 2〜6 で作成したテスト合計）

- [ ] **Step 6: コミット**

```bash
git add api/routers/stream.py api/tests/test_stream.py
git commit -m "feat: add WebSocket /stream/{session_id} endpoint"
```

---

## Task 7: main.py 完成 & Docker スモークテスト

**Files:**

- Modify: `api/main.py`（static files マウント追加）

---

- [ ] **Step 1: `api/main.py` に static files マウントを追加する**

```python
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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
    app.mount("/ai-callcenter", StaticFiles(directory="widget"), name="widget")
```

- [ ] **Step 2: `.env` を用意する（`.env.example` からコピー）**

```bash
cp .env.example .env
# ANTHROPIC_API_KEY を実際の値に書き換える（テスト環境のみ）
```

- [ ] **Step 3: コンテナを起動する**

```bash
docker compose up -d
docker compose logs api
```

Expected: `Application startup complete.` が出力されること。

- [ ] **Step 4: `/analyze` エンドポイントの疎通確認**

```bash
curl -s -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "東京都新宿区で水道管から水漏れが発生しています"}' | jq .
```

Expected（ANTHROPIC_API_KEY が有効な場合）:

```json
{
  "genre": "水道",
  "category": "漏水",
  "address": "東京都新宿区",
  "consultation": "水道管からの水漏れ"
}
```

Expected（API キー未設定の場合）: `401` エラー（API キーが必要なことを確認）

- [ ] **Step 5: コミット**

```bash
git add api/main.py
git commit -m "feat: mount widget static files and complete main.py"
```

---

## Task 8: JS ウィジェット

**Files:**

- Create: `widget/audio-processor.js`
- Create: `widget/widget.js`
- Create: `widget/test.html`

---

- [ ] **Step 1: `widget/audio-processor.js` を作成する**

AudioWorkletProcessor: マイクの Float32 PCM を Google STT 用の Int16 LINEAR16 に変換する。

```javascript
class AudioProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0];
    if (input.length > 0) {
      const channelData = input[0];
      const int16 = new Int16Array(channelData.length);
      for (let i = 0; i < channelData.length; i++) {
        int16[i] = Math.max(-32768, Math.min(32767, channelData[i] * 32768));
      }
      // ArrayBuffer を転送（コピーではなく移動）
      this.port.postMessage(int16.buffer, [int16.buffer]);
    }
    return true;
  }
}

registerProcessor("audio-processor", AudioProcessor);
```

- [ ] **Step 2: `widget/widget.js` を作成する**

```javascript
const AIWidget = (() => {
  let ws = null;
  let audioContext = null;
  let mediaStream = null;
  let workletNode = null;
  let sessionId = null;

  function fillForm(analysis) {
    for (const [key, value] of Object.entries(analysis)) {
      const el = document.querySelector(`[data-ai-target="${key}"]`);
      if (el && value) el.value = value;
    }
  }

  async function startRecording() {
    const wsUrl = window.AI_WIDGET_WS_URL || "ws://localhost:8000";
    ws = new WebSocket(`${wsUrl}/stream/${sessionId}`);

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === "analysis") {
        fillForm(msg.analysis);
      }
    };

    ws.onerror = (err) => console.error("[AIWidget] WebSocket error:", err);

    await new Promise((resolve, reject) => {
      ws.onopen = resolve;
      ws.onerror = reject;
    });

    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioContext = new AudioContext({ sampleRate: 16000 });

    await audioContext.audioWorklet.addModule(
      "/ai-callcenter/audio-processor.js",
    );

    const source = audioContext.createMediaStreamSource(mediaStream);
    workletNode = new AudioWorkletNode(audioContext, "audio-processor");
    workletNode.port.onmessage = (e) => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(e.data);
      }
    };
    source.connect(workletNode);
  }

  function stopRecording() {
    workletNode?.disconnect();
    mediaStream?.getTracks().forEach((t) => t.stop());
    audioContext?.close();
    ws?.close();
    ws = null;
    audioContext = null;
    mediaStream = null;
    workletNode = null;
  }

  function init(options) {
    sessionId = options.sessionId;
    const btn = document.getElementById("ai-start");
    if (!btn) return;
    let recording = false;
    btn.addEventListener("click", async () => {
      if (!recording) {
        recording = true;
        btn.textContent = "⏹ 停止";
        btn.disabled = true;
        try {
          await startRecording();
        } finally {
          btn.disabled = false;
        }
      } else {
        recording = false;
        btn.textContent = "🎤 文字起こし開始";
        stopRecording();
      }
    });
  }

  return { init };
})();
```

- [ ] **Step 3: `widget/test.html` を作成する**

```html
<!DOCTYPE html>
<html lang="ja">
  <head>
    <meta charset="UTF-8" />
    <title>AI コールセンター ウィジェット テスト</title>
    <style>
      body {
        font-family: sans-serif;
        max-width: 600px;
        margin: 2rem auto;
        padding: 0 1rem;
      }
      label {
        display: block;
        margin: 0.5rem 0;
      }
      input,
      textarea {
        width: 100%;
        margin-top: 0.25rem;
        padding: 0.4rem;
        box-sizing: border-box;
      }
      button {
        margin-top: 1rem;
        padding: 0.6rem 1.2rem;
        font-size: 1rem;
        cursor: pointer;
      }
    </style>
  </head>
  <body>
    <h1>AI コールセンター テスト画面</h1>
    <form>
      <label>
        ジャンル
        <input name="genre" data-ai-target="genre" placeholder="（自動入力）" />
      </label>
      <label>
        カテゴリー
        <input
          name="category"
          data-ai-target="category"
          placeholder="（自動入力）"
        />
      </label>
      <label>
        住所
        <input
          name="address"
          data-ai-target="address"
          placeholder="（自動入力）"
        />
      </label>
      <label>
        相談内容
        <textarea
          name="consultation"
          data-ai-target="consultation"
          rows="4"
          placeholder="（自動入力）"
        ></textarea>
      </label>
    </form>

    <button id="ai-start">🎤 文字起こし開始</button>

    <script>
      window.AI_WIDGET_WS_URL = "ws://localhost:8000";
    </script>
    <script src="/ai-callcenter/widget.js"></script>
    <script>
      AIWidget.init({ sessionId: "test-" + Date.now() });
    </script>
  </body>
</html>
```

- [ ] **Step 4: テストページにアクセスして手動テストを行う**

1. ブラウザで `http://localhost:8000/ai-callcenter/test.html` を開く
2. 「🎤 文字起こし開始」ボタンをクリック（マイクアクセスを許可する）
3. モック STT モードの場合: 数秒後にモック文字起こしが届き、Claude API がフォームに自動入力する
4. 実際の API キーがある場合: 話した内容がフォームに反映されることを確認

- [ ] **Step 5: コミット**

```bash
git add widget/
git commit -m "feat: add JS widget with AudioWorklet and WebSocket"
```

---

## Task 9: エンドツーエンド確認

**Files:** なし（手動テスト・ドキュメント）

---

- [ ] **Step 1: 全テストが通ることを最終確認する**

```bash
docker compose run --rm api pytest -v
```

Expected: 全テスト `passed`、`failed` 0件。

- [ ] **Step 2: コンテナが正常起動していることを確認する**

```bash
docker compose ps
```

Expected: `api` が `Up` 状態。

- [ ] **Step 3: モック STT でのエンドツーエンド動作確認**

```bash
# WebSocket 接続テスト（wscat が必要: npm install -g wscat）
wscat -c ws://localhost:8000/stream/e2e-test
```

Expected:

```json
{ "type": "connected", "session_id": "e2e-test" }
```

接続後、Ctrl+C で切断する。

- [ ] **Step 4: ブラウザで test.html を使ったエンドツーエンド動作確認**

1. `http://localhost:8000/ai-callcenter/test.html` を開く
2. ボタンを押してマイクを許可
3. 数秒後にフォームが自動入力されることを確認（モック STT 使用時）
4. `ANTHROPIC_API_KEY` が設定されている場合: フォームに実際の分析結果が入力される
5. ボタンを再押下して録音停止

- [ ] **Step 5: 最終コミット**

```bash
git add .
git commit -m "feat: Phase 1 prototype complete"
```

---

## 未解決事項（Phase 2 以降）

| 項目                  | 内容                                                                                                |
| --------------------- | --------------------------------------------------------------------------------------------------- |
| Google Cloud API キー | `GOOGLE_APPLICATION_CREDENTIALS` に JSON キーファイルを設定すれば実 STT が有効になる                |
| Avaya 連携            | Phase 2 で IT 部門と確認後、`services/stt.py` の入力部分を差し替える                                |
| Laravel 保存 API      | Phase 3 で `routers/stream.py` の `handle_transcripts` に `POST /api/ai-callcenter/sessions` を追加 |
| HTTPS / WSS           | 本番環境ではリバースプロキシ（nginx）で TLS 終端する                                                |
