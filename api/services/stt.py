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
        stt_client = speech.SpeechClient()
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
        responses = stt_client.streaming_recognize(streaming_config, requests)
        for response in responses:
            for result in response.results:
                transcript = result.alternatives[0].transcript
                is_final = result.is_final
                asyncio.run_coroutine_threadsafe(
                    transcript_queue.put((transcript, is_final)), loop
                )

    await loop.run_in_executor(None, run_stt)
    await transcript_queue.put((None, None))
