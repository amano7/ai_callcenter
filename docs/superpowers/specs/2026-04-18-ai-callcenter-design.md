# AI コールセンター 設計仕様書

作成日: 2026-04-18

---

## 概要

顧客からの電話をリアルタイムにテキスト化し、ジャンル・カテゴリー・住所・相談内容を判定して JSON として保存するアプリ。

**最終目標：** 既存の Laravel Blade フォームに JS ウィジェットとして組み込み、ボタン操作で文字起こしを開始し、フォームの各入力項目に自動入力する。

---

## 要件

| 項目                     | 内容                                                        |
| ------------------------ | ----------------------------------------------------------- |
| 主要ユーザー             | コールセンターオペレーター（通話中にリアルタイム確認）      |
| 同時通話数               | 50件以上（本番想定）                                        |
| UI                       | 独立した画面は不要。既存 Laravel Blade フォームへの埋め込み |
| 電話システム             | Avaya（詳細バージョン・環境はIT部門に要確認）               |
| 音声取得（プロトタイプ） | ブラウザのマイク入力（Web Audio API）                       |
| 音声取得（本番）         | Avaya 連携（Chrome 拡張経由の可能性あり・要調査）           |

---

## 技術スタック

| 役割              | 技術                                                |
| ----------------- | --------------------------------------------------- |
| 既存フォーム統合  | JS ウィジェット（Vanilla JS）                       |
| Web UI・保存 API  | Laravel 12（既存アプリに追加）                      |
| 音声処理・AI 分析 | Python 3.12 + FastAPI                               |
| 音声文字起こし    | Google Cloud Speech-to-Text（日本語ストリーミング） |
| 構造化データ抽出  | Claude API（`claude-sonnet-4-6`）                   |
| リアルタイム通信  | WebSocket（FastAPI ネイティブ）                     |
| DB                | 既存 Laravel の DB（MySQL 等）をそのまま使用        |
| 開発環境          | Docker Compose                                      |

---

## 全体アーキテクチャ

```
【既存 Laravel Blade 画面】
┌────────────────────────────────────────┐
│  [氏名______] [住所__________]         │
│  [相談内容_________________________]   │
│                                        │
│  🎤 [文字起こし開始] ← JS ウィジェット │
└────────────────────────────────────────┘
         ↕ WebSocket
【Python FastAPI サービス】
  ├─ 音声受信（ブラウザマイク → 後に Avaya）
  ├─ Google Cloud STT（日本語ストリーミング）
  └─ Claude API（住所・カテゴリ等の構造化抽出）
         ↕
【Laravel（既存アプリ）】
  ├─ JS ウィジェットの配信
  └─ 結果 JSON の保存 API
```

---

## コンポーネント詳細

### 1. JS ウィジェット

既存の Blade テンプレートへの組み込みイメージ：

```html
<!-- 既存フォームの input に data属性を追加 -->
<input name="address" data-ai-target="address" />
<input name="category" data-ai-target="category" />
<textarea name="content" data-ai-target="consultation"></textarea>

<!-- 開始ボタン -->
<button id="ai-start">🎤 文字起こし開始</button>

<!-- ウィジェット読み込み -->
@push('scripts')
<script src="/ai-callcenter/widget.js"></script>
<script>
  AIWidget.init({ sessionId: "{{ $callId }}" });
</script>
@endpush
```

**動作フロー：**

1. ボタン押下 → マイク録音開始 → Python へ WebSocket 送信
2. Python から文字起こし・構造化データが届く → `data-ai-target` 属性を見てフォームに自動入力
3. ボタン再押下 → 録音停止・セッション終了

---

### 2. Python FastAPI サービス

| エンドポイント            | 役割                                         |
| ------------------------- | -------------------------------------------- |
| `WS /stream/{session_id}` | 音声受信 + 結果送信（双方向 WebSocket）      |
| `POST /analyze`           | テキストのみ構造化抽出（テスト・デバッグ用） |

**処理フロー：**

```
音声チャンク受信（ブラウザから WebSocket）
  → Google Cloud STT（ストリーミング認識）
  → テキストをバッファに蓄積
  → 30秒分 or 200文字分溜まったら Claude API へ送信
  → {genre, category, address, consultation} を JSON で取得
  → WebSocket でブラウザへ push（フォーム自動入力）
  → Laravel 保存 API へ POST（DB 保存）
```

**Claude へのプロンプト設計（抽出項目）：**

- `genre` : 相談ジャンル
- `category` : サブカテゴリー
- `address` : 顧客の住所
- `consultation` : 相談内容の要約

---

### 3. Laravel 側の追加実装

既存アプリへの追加分のみ（新規アプリは作らない）：

| 追加内容           | 詳細                                                                           |
| ------------------ | ------------------------------------------------------------------------------ |
| `widget.js` の配信 | `public/ai-callcenter/widget.js` として配置                                    |
| 保存 API           | `POST /api/ai-callcenter/sessions`                                             |
| DB テーブル        | `ai_call_sessions`（session_id, call_id, transcript, result_json, created_at） |

---

## パフォーマンス設計

| 観点              | 方針                                                                                  |
| ----------------- | ------------------------------------------------------------------------------------- |
| レイテンシ        | STT: 〜500ms、AI構造化: 1〜3秒。オペレーターの確認・修正用途なので許容範囲            |
| 50件同時対応      | FastAPI は非同期処理で数十接続を1プロセスで処理可能。本番は複数コンテナで水平スケール |
| Claude API コスト | 毎秒ではなく「30秒 or 200文字」バッファリングで呼び出し頻度を制御                     |
| Google STT コスト | ストリーミング: 約 $0.016/分。50通話 × 8時間 = 要コスト試算                           |

---

## 開発フェーズ

### Phase 1（プロトタイプ）

- ブラウザマイク入力で動作確認
- Python FastAPI + Google STT + Claude API の連携
- JS ウィジェットの基本動作（録音 → フォーム自動入力）
- Docker Compose でローカル動作

### Phase 2（Avaya 連携調査）

- Avaya の環境・バージョンを IT 部門に確認
- Chrome 拡張からの音声取得可能性を検証
  - Avaya がブラウザベース（WebRTC）であれば `tabCapture` API で取得できる可能性あり
  - 物理電話機 + オンプレの場合は SIP/RTP ストリームをサーバー側でキャプチャする構成に変更
- 音声入力モジュールを差し替えるだけで対応できるよう Phase 1 から分離した設計にしておく

### Phase 3（既存 Laravel アプリへの統合）

- `widget.js` を既存 Blade ページに組み込む
- フォームフィールドマッピングの調整
- 本番環境での負荷テスト

---

## 未解決事項（要調査）

| 項目                                             | 担当           | 期限           |
| ------------------------------------------------ | -------------- | -------------- |
| Avaya の環境（オンプレ / クラウド / バージョン） | IT 部門        | Phase 2 開始前 |
| Chrome 拡張からの Avaya 音声取得可否             | IT 部門 + 開発 | Phase 2        |
| Google Cloud / AWS アカウントの用意              | インフラ担当   | Phase 1 完了前 |
| Claude API キーの発行                            | 開発担当       | Phase 1 開始時 |
