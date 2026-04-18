import asyncio
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.claude import extract_fields
from services.stt import create_stt_session

router = APIRouter()

_BUFFER_MAX_CHARS = 50
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
                # セッション終了時に残りのバッファをフラッシュ
                if transcript_buffer.strip():
                    text = transcript_buffer.strip()
                    try:
                        analysis = await extract_fields(text)
                        await websocket.send_json(
                            {"type": "analysis", "analysis": analysis.model_dump()}
                        )
                    except Exception as e:
                        try:
                            await websocket.send_json({"type": "error", "message": str(e)})
                        except RuntimeError:
                            pass
                break
            try:
                await websocket.send_json(
                    {"type": "transcript", "text": transcript, "is_final": is_final}
                )
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
                await websocket.send_json(
                    {"type": "analysis", "analysis": analysis.model_dump()}
                )
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
