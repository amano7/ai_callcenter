# ローカル Whisper 導入設計

**日付**: 2026-04-21  
**ブランチ**: `feature/local-whisper`  
**目的**: Google Cloud STT を OpenAI Whisper（ローカル実行）に置き換え、月額 $11,520 → $0 へのコスト削減

---

## 1. 概要

現在の Phase 1 プロトタイプは Google Cloud STT で日本語ストリーミング文字起こしを実現しています。本タスクでは、Google Cloud STT に代わってローカル OpenAI Whisper を導入し、**既存インターフェースは変えずに内部実装のみ置き換え**ます。

### コスト削減効果

| 項目                   | Google STT                 | ローカル Whisper |
| ---------------------- | -------------------------- | ---------------- |
| **月額コスト**         | $11,520（50通話×480分/日） | $0               |
| **削減額**             | —                          | 100% 削減        |
| **日本語対応**         | ◎                          | ◎                |
| **ストリーミング対応** | ◎                          | ◎（新規実装）    |

---

## 2. 技術方式

### 2-1. Whisper モデル選択

- **モデル**: OpenAI Whisper v3 small
- **サイズ**: 483MB
- **言語**: 日本語対応 ✓
- **推論速度**: 中程度（MacBook M4 で 1 秒のオーディオ = 0.2～0.3 秒で推論）
- **精度**: 中高（このユースケースで十分）

**選定理由**: 精度と推論速度のバランスが最適。tiny/base では精度が低く、medium/large は推論が遅すぎる。

### 2-2. ストリーミング実装方式：連続推論

Google STT のストリーミング方式（リアルタイムに中間結果を返す）を、Whisper でも実現します。

```
【音声受信】
ブラウザから 256 バイトチャンク × 連続送信
16kHz × 16bit で = 約 8ms 分ずつ

【バッファリング】
サーバー側で 1 秒分（= 16,000 サンプル）をバッファ

【Whisper 推論】
1 秒ごとに バッファ内容を Whisper に送信
↓
結果を is_final=False で WebSocket push（中間結果）

【停止時】
バッファ内の残りの音声を Whisper に送信
↓
結果を is_final=True で返す（確定結果）
```

### 2-3. 推論タイミング

- **間隔**: 1 秒（1000ms）ごと
- **理由**:
  - Whisper small の推論時間 = 数秒
  - 1 秒ごとに呼べば、最新の文字起こしが常に「数秒遅れ」で返される
  - ユーザー体感としては十分なリアルタイム性
  - CPU/メモリ負荷が適度

### 2-4. 精度への考慮

短い音声片（1 秒分）での認識精度を保つため：

- **前のバッファ情報は加味しない** — 毎回 1 秒分のみを独立認識
- **本番での精度改善オプション**:
  - バッファサイズを 2～3 秒に増やす → 精度向上（ただしリアルタイム性低下）
  - `fp16=True` などの推論パラメータ調整

---

## 3. 実装計画

### 3-1. 変更ファイル一覧

| ファイル               | 変更内容                                               | 影響範囲     |
| ---------------------- | ------------------------------------------------------ | ------------ |
| `api/requirements.txt` | `openai-whisper` パッケージ追加                        | 依存関係     |
| `api/main.py`          | FastAPI 起動時に Whisper モデルをロード                | 初期化       |
| `api/services/stt.py`  | `_whisper_stt()` 関数追加、`create_stt_session()` 拡張 | STT ロジック |

### 3-2. インターフェース（互換性維持）

既存の asyncio Queue ベースインターフェースをそのまま使用。呼び出し側の変更なし。

```python
async def create_stt_session(
    audio_queue: asyncio.Queue,   # 音声入力
    transcript_queue: asyncio.Queue,  # 文字起こし結果
) -> None:
    """STT セッション（Google / Whisper / モック を自動切り替え）"""
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        if os.environ.get("USE_LOCAL_WHISPER"):
            await _whisper_stt(audio_queue, transcript_queue)
        else:
            await _mock_stt(audio_queue, transcript_queue)
    else:
        await _google_stt(audio_queue, transcript_queue)
```

### 3-3. 環境変数

`.env` に追加：

```bash
# STT プロバイダ選択
# 未設定または USE_LOCAL_WHISPER=false → モック STT
# USE_LOCAL_WHISPER=true → ローカル Whisper
# GOOGLE_APPLICATION_CREDENTIALS 設定済み → Google STT
USE_LOCAL_WHISPER=true
```

---

## 4. テスト戦略

### 4-1. 既存テストの互換性

- `tests/test_stream.py` などは変更不要
- インターフェース（Queue ベース）が同じため、既存テストスイートは Whisper でも動作

### 4-2. 動作確認

1. **ローカルテスト**:
   - テストページ（`/ai-callcenter/test.html`）で手動テスト
   - 「文字起こし開始」ボタン → マイク許可 → 何か喋る → 1 秒ごとに文字起こしが画面に出る
   - 停止 → フォーム自動入力

2. **Docker コンテナテスト**:
   ```bash
   docker compose up -d
   curl http://localhost:8000/ai-callcenter/test.html
   ```

### 4-3. 成功基準

- ✓ 1 秒ごとに中間結果が WebSocket に push される
- ✓ 話の途中で文字起こしがリアルタイムに画面に出る
- ✓ 停止後、Claude の構造化抽出が正常に動作
- ✓ フォームに自動入力される
- ✓ 既存テスト（pytest）は全て成功

---

## 5. リスク・制約

### 5-1. 推論速度の遅延

- **リスク**: Whisper small でも 1 秒分の推論に 0.2～0.3 秒かかる可能性
- **対策**: 実装後のベンチマークで確認。必要に応じてバッファサイズを調整

### 5-2. CPU / メモリ負荷

- **リスク**: Docker コンテナ（CPU 制限あり）で Whisper を常時実行
- **対策**:
  - リソース監視（`docker stats`）で確認
  - 必要に応じて `docker-compose.yml` の CPU/メモリ制限を調整

### 5-3. 日本語精度

- **リスク**: Whisper v3 small は Google STT ほどの精度がない可能性
- **対策**:
  - 実装後、ノイズのある音声で精度テスト
  - 必要に応じて medium モデルに変更検討

---

## 6. 次のステップ

本設計承認後、以下を実装：

1. **`openai-whisper` のインストール** → requirements.txt 更新、Docker ビルド
2. **`_whisper_stt()` 関数実装** → 1 秒バッファリング + Whisper 推論ロジック
3. **モデルロード処理追加** → FastAPI `startup` イベントで Whisper モデルを初期化
4. **テスト実行** → テストページで動作確認、既存テスト成功確認
5. **パフォーマンス計測** → 推論時間、CPU/メモリ使用率ログ
6. **本番マージ** → 動作確認後 main ブランチにマージ

---

## 7. 参考資料

- [OpenAI Whisper GitHub](https://github.com/openai/whisper)
- [Whisper v3 日本語対応](https://openai.com/research/whisper)
- 既存実装: `/Users/amano7/docker/pecos/ai_callcenter/api/services/stt.py`
