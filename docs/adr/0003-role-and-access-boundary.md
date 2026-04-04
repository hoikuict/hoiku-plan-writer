# ADR 0003: Role And Access Boundary

## Status

Accepted

## Context

`open-hoikuict` では、認証そのものと業務権限判定を分離しつつ、`role` をもとに編集可否を決める構成が採られている。また、保育計画文書では「誰が」「どの園で」「どのクラスの文書を」扱えるかが重要であり、本体統合時にもこの境界を保つ必要がある。

## Decision

この repo では、認証情報を次の 3 軸で扱う。

- `role`
- `nursery_ref`
- `classroom_refs`

ロール値は `open-hoikuict` と揃えて以下を採用する。

- `view_only`
- `can_edit`
- `admin`

権限制御は以下の原則で行う。

- 閲覧は `view_only` 以上で可能
- 下書き作成・更新は `can_edit` 以上で可能
- 承認・差戻し・有効化は `admin` のみ可能
- 文書の参照範囲は `nursery_ref` と `classroom_refs` で制限する

認証実装はバックエンド差し替え可能にし、初期段階では cookie ベースのモック認証を使う。

## Consequences

- `open-hoikuict` 本体の認証基盤へ差し替えやすい
- 画面・サービス層は `current_user` の契約だけを見ればよい
- 本体統合時に role と所属の解決先を置き換えやすい
- 一方で、将来 SSO や本番認証へ切り替える際は role マッピングの検証が必要になる
