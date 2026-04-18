# AI Call Center

## 概要

コールセンターオペレーター向けのリアルタイム通話文字起こし・AI分析ツール。

顧客からの電話をリアルタイムにテキスト化し、ジャンル・カテゴリー・住所・相談内容を判定して JSON として保存する。

**最終目標:** 既存の Laravel Blade フォームに JS ウィジェットとして組み込み、ボタン操作で文字起こしを開始し、フォーム項目に自動入力する。

## 技術スタック

| 役割             | 技術                                                |
| ---------------- | --------------------------------------------------- |
| フォーム統合     | JS ウィジェット（Vanilla JS）                       |
| Web / 保存 API   | Laravel 12（既存アプリに追加）                      |
| 音声処理・AI     | Python 3.12 + FastAPI                               |
| 文字起こし       | Google Cloud Speech-to-Text（日本語ストリーミング） |
| 構造化抽出       | Claude API（claude-sonnet-4-6）                     |
| リアルタイム通信 | WebSocket（FastAPI）                                |
| 開発環境         | Docker Compose                                      |

## アーキテクチャ概要

```
既存 Laravel Blade フォーム
  └─ JS ウィジェット（data-ai-target 属性でフォーム項目に自動入力）
         ↕ WebSocket
Python FastAPI サービス
  ├─ Google Cloud Speech-to-Text（文字起こし）
  └─ Claude API（ジャンル・カテゴリー・住所・相談内容を抽出）
         ↕
Laravel（既存アプリ） → DB 保存
```

## 開発フェーズ

- **Phase 1（プロトタイプ）**: ブラウザマイク入力 → 文字起こし → フォーム自動入力
- **Phase 2（Avaya 連携）**: Avaya からの音声取得（IT部門と連携）
- **Phase 3（本番統合）**: 既存 Laravel アプリへの組み込み

## ドキュメント

- 詳細設計仕様: `docs/superpowers/specs/2026-04-18-ai-callcenter-design.md`
- 開発ガイド: `CLAUDE.md`
