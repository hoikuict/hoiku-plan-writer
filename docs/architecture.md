# 初期アーキテクチャ

## 継承元

この repo は `open-hoikuict` のスピンアウトとして、次の設計思想を継承する。

- FastAPI をアプリ入口にする
- SQLModel を永続化に使う
- Jinja2 + HTMX でサーバ中心の画面を組む
- role ベースで画面操作を制御する
- 認証バックエンドは差し替え可能にする

## この repo の境界

この repo は「保育計画文書」だけを扱う bounded context とする。

### 内部で保持するもの

- 園プロファイル
- 年間指導計画 / 月案
- セクション単位の文書ブロック
- 承認ログ

### 外部とつなぐ安定契約

- `nursery_ref`
- `classroom_ref`
- `actor_ref`
- `section_key`
- `document_status`
- `source_refs`
- `evidence_tags`

### あえて持たないもの

- 園児、家庭、出欠など本体既存モデルへの直接依存
- 本体 DB テーブルへの外部キー
- 単一 DB 前提の密結合

## レイヤー

- `web`
  FastAPI ルーター、Jinja2 テンプレート、HTMX 部分更新
- `auth`
  role / nursery / classroom scope を含む職員セッション契約
- `persistence`
  SQLModel テーブル定義と repository
- `domain`
  文書生成に使う純粋なドメインモデル
- `services`
  年間計画・月案の生成ロジック

## 実装方針

- HTML 画面を先に成立させる
- JSON API は必要になるまで主経路にしない
- 文書は全文テキストではなくブロック構造で保持する
- 後の本体統合は adapter を追加して対応する
