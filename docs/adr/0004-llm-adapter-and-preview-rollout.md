# ADR 0004: LLM Adapter and Preview-first Rollout

## Status
Accepted

## Context
この repo では、園プロファイルを軸に年間指導計画と月案を生成する。
将来は本体統合を前提にするが、現時点では本体業務モデルや本体 DB へ直接依存させたくない。
また、LLM を導入してもサーバ中心の画面構成、role 制御、人手レビュー前提の運用は維持したい。

既存実装には `services/generators.py` によるルールベース生成がある。
これは未設定時の動作保証と、人手確認しやすい基準案として価値がある。

## Decision
次の方針を採る。

- LLM は `web` から直接呼ばず、`ai/` 配下の adapter 経由で利用する。
- `services/generators.py` は廃止せず、基準案とフォールバックとして残す。
- 第1段階では provider 差し替え可能な AI 境界を追加する。
- 第2段階では年間指導計画のプレビューだけを AI サービス経由にする。
- 文書保存は引き続き既存 generator を使い、preview と persistence を切り分ける。
- LLM の出力は structured JSON に限定し、`GeneratedPlan` へ変換してから UI に渡す。
- 最初のローカル provider は Ollama とし、既定モデルは `qwen2.5:0.5b` とする。
- 画面から `LLMプレビューを使う` のオン・オフを切り替えられるようにし、オフ時は即座に rule-based generator に戻す。
- OpenAI などの外部 provider は代替 provider として追加可能にする。

## Consequences
### Positive
- ローカルの TrueNAS / Docker / Ollama 構成に乗せやすい。
- LLM 未設定でもアプリが成立する。
- 年間計画 preview から小さく導入できる。
- 月案生成、AI レビュー、ブロック単位再生成へ横展開しやすい。
- 将来の本体統合でも、`ai/` と `domain` の境界を維持しやすい。

### Negative
- preview と save で一時的に生成経路が異なる。
- provider ごとの応答差異を `ai/contracts.py` で吸収する必要がある。
- CPU-only の Ollama ではモデルサイズ次第で preview が遅くなる。
- LLM 導入直後は observability と失敗時メッセージを継続的に整える必要がある。

## Notes
今後の段階的拡張は次を前提にする。

1. annual preview を AI 化
2. monthly preview / generate を AI 化
3. AI review を追加
4. section 単位の再生成に拡張