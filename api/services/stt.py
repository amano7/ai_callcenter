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
    """STT セッション。USE_LOCAL_WHISPER / GOOGLE_APPLICATION_CREDENTIALS の設定に応じて切り替え。"""
    if os.environ.get("USE_LOCAL_WHISPER") == "true":
        await _whisper_stt(audio_queue, transcript_queue)
    elif os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        await _google_stt(audio_queue, transcript_queue)
    else:
        await _mock_stt(audio_queue, transcript_queue)


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
            model="telephony",
            use_enhanced=True,
            enable_automatic_punctuation=True,
        )
        streaming_config = speech.StreamingRecognitionConfig(
            config=config,
            interim_results=True,
        )
        requests = (
            speech.StreamingRecognizeRequest(audio_content=chunk)
            for chunk in audio_generator()
        )
        try:
            responses = stt_client.streaming_recognize(streaming_config, requests)
            for response in responses:
                for result in response.results:
                    transcript = result.alternatives[0].transcript
                    is_final = result.is_final
                    print(f"[stt] transcript: {transcript!r} (final={is_final})", flush=True)
                    asyncio.run_coroutine_threadsafe(
                        transcript_queue.put((transcript, is_final)), loop
                    )
        except Exception as e:
            print(f"[stt] error: {e}", flush=True)
            raise

    await loop.run_in_executor(None, run_stt)
    await transcript_queue.put((None, None))


async def _whisper_stt(
    audio_queue: asyncio.Queue,
    transcript_queue: asyncio.Queue,
) -> None:
    """ローカル Whisper ストリーミング（1秒ごとの連続推論）"""
    import numpy as np
    from main import _whisper_model

    # 音声バッファ（16kHz × 16bit = 16,000 サンプル/秒）
    sample_rate = 16000
    buffer_duration = 4.0  # 4 秒（base モデルの推論時間とバランス）
    buffer_samples = int(sample_rate * buffer_duration)

    # バッファをリストで管理（ミュータブル）
    buffer_list = []
    loop = asyncio.get_event_loop()

    def run_whisper_inference():
        """Whisper 推論（スレッドプールで実行）"""
        if len(buffer_list) < buffer_samples:
            return None  # バッファがまだ満たない

        # バッファから 1 秒分を抽出
        audio_chunk = np.array(buffer_list[:buffer_samples], dtype=np.float32)

        # 残りのバッファを保持（リストから削除）
        del buffer_list[:buffer_samples]

        try:
            # Whisper で推論
            result = _whisper_model.transcribe(
                audio_chunk,
                language="ja",
                fp16=False,
            )
            transcript = result.get("text", "").strip()
            return transcript if transcript else None
        except Exception as e:
            print(f"[stt] Whisper error: {e}", flush=True)
            return None

    try:
        while True:
            # 音声チャンクを受信
            chunk = await audio_queue.get()
            if chunk is None:
                break

            # バイナリデータを float32 に変換
            # chunk: bytes（Int16 形式）
            chunk_int16 = np.frombuffer(chunk, dtype=np.int16)
            chunk_float32 = chunk_int16.astype(np.float32) / 32768.0

            # バッファに追加（リストに拡張）
            buffer_list.extend(chunk_float32.tolist())

            # バッファが 1 秒以上たまったら推論
            while len(buffer_list) >= buffer_samples:
                transcript = await loop.run_in_executor(None, run_whisper_inference)
                if transcript:
                    print(f"[stt] transcript: {transcript!r} (final=False)", flush=True)
                    await transcript_queue.put((transcript, False))

        # 残りのバッファを最後に推論
        if len(buffer_list) > 0:
            # 残りのバッファをパディング（不足分をゼロ埋め）
            padded = buffer_list + [0.0] * (buffer_samples - len(buffer_list))
            padded_array = np.array(padded[:buffer_samples], dtype=np.float32)

            try:
                result = _whisper_model.transcribe(
                    padded_array,
                    language="ja",
                    fp16=False,
                )
                transcript = result.get("text", "").strip()
                if transcript:
                    print(f"[stt] transcript: {transcript!r} (final=True)", flush=True)
                    await transcript_queue.put((transcript, True))
            except Exception as e:
                print(f"[stt] Whisper error on final buffer: {e}", flush=True)

    except Exception as e:
        print(f"[stt] error: {e}", flush=True)
        raise
    finally:
        await transcript_queue.put((None, None))
