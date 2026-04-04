# ADR 0001: Server-Centered Web Stack

## Status

Accepted

## Context

この repo は `open-hoikuict` から独立公開するスピンアウトである。一方で、将来は本体へ統合する前提があるため、利用技術と画面構成は可能な限り `open-hoikuict` に揃えておく必要がある。

参照した `open-hoikuict` では以下の特徴が見られた。

- `FastAPI` をアプリケーション入口とし、機能単位に `APIRouter` を分割する
- `SQLModel` を永続化モデルとセッション管理に用いる
- `Jinja2Templates` を使い、HTML をサーバ側で描画する
- `HTMX` を使って一覧更新や部分再描画を補助する
- JSON API を先に作るのではなく、業務画面を先に成立させる

## Decision

この repo でも、MVP の標準構成として以下を採用する。

- `FastAPI + SQLModel + Jinja2 + HTMX`
- サーバ中心の HTML 画面を主経路とする
- ルーターは業務機能単位に分割する
- クライアント側 JavaScript は最小限に留め、画面遷移・保存・レビューはフォーム送信中心にする
- HTMX はプレビュー、一覧絞り込み、部分更新など限定的な補助に使う

## Consequences

- `open-hoikuict` 本体に寄せた運用・保守感覚を維持しやすい
- SPA や専用 API を前提にしないため、初期実装を小さく始めやすい
- 将来統合時に、テンプレート、認証依存、ルーター構成を揃えやすい
- 一方で、リッチなフロントエンド体験は必要箇所だけ後付けする前提になる
