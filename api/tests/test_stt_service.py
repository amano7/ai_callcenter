import asyncio
from services.stt import create_stt_session


async def test_mock_stt_returns_transcript_on_audio_chunk():
    """GOOGLE_APPLICATION_CREDENTIALS 未設定時はモック STT が動作する。"""
    audio_queue: asyncio.Queue = asyncio.Queue()
    transcript_queue: asyncio.Queue = asyncio.Queue()

    await audio_queue.put(b"\x00" * 1024)
    await audio_queue.put(None)

    await create_stt_session(audio_queue, transcript_queue)

    transcript, is_final = await transcript_queue.get()
    assert isinstance(transcript, str)
    assert len(transcript) > 0
    assert is_final is True

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
