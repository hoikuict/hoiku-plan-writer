# Contracts

## Purpose
この文書は、単独版と `open-hoikuict` 本体の間で将来共有・統合されうる契約を定義する。
ここで定義したキー名、状態名、参照形式は、原則として後方互換を維持する。

## Roles
- `admin`: 園管理者。承認、差戻し、profile active化ができる。
- `teacher`: 担任・クラス担当。作成、編集、生成、レビュー依頼ができる。

## Document Types
- `nursery_profile`
- `annual_plan`
- `monthly_plan`

## Document Status
- `draft`
- `in_review`
- `approved`
- `rejected`
- `archived`

### Status Semantics
- `draft`: 編集・生成可能
- `in_review`: レビュー待ち
- `approved`: 正式版
- `rejected`: 差戻し済み
- `archived`: 旧版参照専用

## Section Key Rules
`section_key` は表示ラベルではなく永続契約である。
UI文言変更では変更しない。

### AnnualPlan section_key
- `annual_goal`
- `term_1_outlook`
- `term_2_outlook`
- `term_3_outlook`
- `term_4_outlook`

### MonthlyPlan section_key
- `monthly_goal`
- `childrens_state`
- `environment`
- `support`
- `family_collaboration`
- `reflection`

## Source Ref Format
`source_refs` は文字列配列とし、以下の prefix を持つ。

- `profile.*`
- `knowledge.*`
- `form.*`
- `annual.*`
- `monthly.*`
- `outline.*`
- `linking.*`

例:
- `profile.philosophy`
- `form.current_children`
- `annual.term_1`
- `knowledge.health_and_safety`

## Evidence Tag Rules
表示タグは `source_refs` から再計算する。

- `profile.*` => `[園方針]`
- `knowledge.*` => `[公的根拠]`
- `form.*`, `annual.*`, `monthly.*` => `[入力]`
- `outline.*`, `linking.*` => `[AI構成]`

各 section は最低1つ以上の evidence tag を持たなければならない。

## External Reference Fields
本体統合を見据え、外部参照は以下の形式で保持する。

- `nursery_ref: str`
- `classroom_ref: str`
- `actor_ref: str`
- `source_system: str`

これらは本体の内部PKとは別に扱う。

## Revision Contract
`PlanRevision` は以下を最低限保持する。

- `document_type`
- `document_id`
- `section_key`
- `revision_type`
- `before_json`
- `after_json`
- `actor_ref`
- `created_at`

## Approval Contract
`ApprovalLog` は以下を最低限保持する。

- `document_type`
- `document_id`
- `action`
- `comment`
- `actor_ref`
- `created_at`

`action` は以下のみ許可する。
- `submit`
- `approve`
- `reject`

## AI Output Contract
AI出力は structured JSON のみ許可する。
最低限以下を含む。

- `document_type`
- `sections[]`
- `sections[].section_key`
- `sections[].title`
- `sections[].body`
- `sections[].source_refs`
- `sections[].needs_confirmation`
- `sections[].editor_note`
- `confirmation_items[]`

## Change Policy
以下は破壊的変更として扱う。

- 既存 `section_key` の変更
- 既存 status 名の変更
- `source_refs` prefix ルールの変更

破壊的変更を行う場合は以下を必須とする。

- ADR 作成
- migration 方針の記述
- 互換レイヤまたは変換スクリプトの用意
