# ADR 0002: Bounded Context And Integration Refs

## Status

Accepted

## Context

この repo で扱う中心業務は「園プロファイル」「年間指導計画」「月案」「レビュー・承認」である。`open-hoikuict` 本体には園児、家庭、出欠、保護者アカウントなど既存業務モデルがあるが、このスピンアウトがそれらに直接依存すると、独立公開もしづらく、本体統合時にも境界が曖昧になる。

継承したいものは本体の設計思想であり、既存業務モデルへの直接参照ではない。

## Decision

本 repo は「保育計画文書」だけを扱う独立した bounded context とする。

### この repo が直接保持するもの

- `NurseryProfile`
- `PlanDocument`
- `PlanBlock`
- `ApprovalLog`

### 本体統合を見据えて安定契約として保持するもの

- `section_key`
- `document_status`
- `source_refs`
- `evidence_tags`
- `actor_ref`
- `classroom_ref`
- `nursery_ref`

### この repo が持たないもの

- 園児、家庭、出欠など本体既存業務モデルへの直接依存
- 本体 DB テーブルへの外部キー
- 単一 DB を共有する前提のテーブル結合

### 参照方法

本体側の主体や所属は、外部キーではなく参照値で扱う。

- `actor_ref`: 例 `staff:demo-admin`
- `classroom_ref`: 例 `classroom:5yo-a`
- `nursery_ref`: 例 `nursery:demo`

## Consequences

- 独立公開時はこの repo 単体で動かせる
- 本体統合時は、参照値を本体の ID 解決アダプタに接続すればよい
- DB を別にしても同じ契約で連携できる
- 一方で、一覧表示や参照名の解決には将来アダプタ層が必要になる
