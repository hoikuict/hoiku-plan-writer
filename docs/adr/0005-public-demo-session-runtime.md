# ADR 0005: Public Demo Session Runtime

- Status: Accepted
- Date: 2026-04-05

## Context

このリポジトリは未完成の段階でも公開デモとして外部公開したい。一方で、`open-hoikuict` と同じく、本体とは切り離した公開ブランチを用意し、利用者同士のデータが混ざらないこと、デモ後に簡単にリセットできることが必要である。

Cloudflare 経由で公開する都合上、HTTPS 終端はアプリ外で行われる。Cookie の `secure` 判定やセッション保持方法もそれに合わせる必要がある。

## Decision

公開デモでは `PUBLIC_DEMO_MODE` を有効にし、以下を採用する。

1. ブラウザごとに `demo_session_id` cookie を払い出す。
2. 各 `demo_session_id` に対して、初期データ入り SQLite を `runtime/sessions/<session_id>/app.sqlite3` として複製する。
3. アプリの通常 DB ではなく、HTTP リクエストごとにそのセッション DB を解決して SQLModel Session を作る。
4. セッション DB は TTL 経過で削除し、入力サイズと累積書き込み量にも上限を設ける。
5. 職員ログイン cookie も session cookie 化し、公開デモではブラウザを閉じると自然にリセットされるようにする。
6. 公開ブランチには Dockge / Cloudflare Tunnel 用の `compose.yaml` と `DEPLOYMENT.md` を同梱する。

## Consequences

- デモ利用者ごとのデータ分離ができる。
- 再デプロイやコンテナ再作成でセッションデータが消えるため、永続運用には向かない。
- `open-hoikuict` の公開デモ分岐と近い構造になるため、将来の運用知見を共有しやすい。
- WebSocket を追加する場合は、HTTP と同じ `demo_session_id` を明示的に引き回す必要がある。