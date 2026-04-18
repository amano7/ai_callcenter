# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

コールセンターオペレーター向けのリアルタイム通話文字起こし・AI分析ツール。

**最終目標:** 既存の Laravel Blade フォームに JS ウィジェットとして組み込み、オペレーターがボタンを押すと通話音声を文字起こしして、フォームの各項目（住所・カテゴリー・相談内容等）に自動入力する。

詳細仕様: `docs/superpowers/specs/2026-04-18-ai-callcenter-design.md`

## 現在のステータス

**Phase 1（プロトタイプ）着手前** — 設計完了、実装未着手。

## アーキテクチャ

```
既存 Laravel Blade フォーム
  └─ JS ウィジェット（data-ai-target 属性でフォーム項目に自動入力）
         ↕ WebSocket
Python FastAPI サービス（Dockerコンテナ）
  ├─ 音声受信（Phase 1: ブラウザマイク / Phase 2: Avaya 連携）
  ├─ Google Cloud Speech-to-Text（日本語ストリーミング文字起こし）
  └─ Claude API claude-sonnet-4-6（ジャンル・カテゴリー・住所・相談内容を構造化抽出）
         ↕
Laravel（既存アプリに API を追加）
  └─ POST /api/ai-callcenter/sessions（結果 JSON を DB 保存）
```

## 技術スタック

| 役割             | 技術                            |
| ---------------- | ------------------------------- |
| フォーム統合     | JS ウィジェット（Vanilla JS）   |
| Web / 保存 API   | Laravel 12（既存アプリに追加）  |
| 音声処理・AI     | Python 3.12 + FastAPI           |
| 文字起こし       | Google Cloud Speech-to-Text     |
| 構造化抽出       | Claude API（claude-sonnet-4-6） |
| リアルタイム通信 | WebSocket（FastAPI）            |
| 開発環境         | Docker Compose                  |

## 開発フェーズ

- **Phase 1（プロトタイプ）**: ブラウザマイク入力 → 文字起こし → JS ウィジェットでフォーム自動入力
- **Phase 2（Avaya 連携）**: IT 部門と連携して Avaya からの音声取得方法を確定・実装
- **Phase 3（本番統合）**: 既存 Laravel アプリへの組み込み・負荷テスト

## 未解決事項

- Avaya の環境（オンプレ / クラウド / バージョン）→ IT 部門に確認
- Chrome 拡張からの Avaya 音声取得可否 → 要調査
- Google Cloud / Claude API キーの用意

## Development Environment

このプロジェクトは `~/docker/` 配下にあるため、Bash コマンドはすべて Docker コンテナ内で実行する。親ディレクトリの `~/docker/CLAUDE.md` の `docker compose exec` ルールに従うこと。

ファイル操作（Read/Edit/Write/Glob/Grep）はホスト側で行う。
