# hoiku-plan-writer

`open-hoikuict` から独立公開する、保育計画文書作成アプリです。FastAPI + SQLModel + Jinja2 + HTMX のサーバ中心構成を引き継ぎつつ、既存業務モデルへの直接依存を避け、本体統合しやすい境界で実装しています。

## 継承しているもの

- FastAPI + SQLModel + Jinja2 + HTMX
- サーバ中心の画面構成
- role ベースの権限制御
- 後から `open-hoikuict` に戻しやすい構造

## 主な画面

- `/staff/login`
  モック職員でログインします。
- `/nursery-profile/`
  園プロファイルを保存し、有効化します。
- `/annual-plans/new`
  年間指導計画をプレビューして作成します。
- `/monthly-plans/new`
  月案をプレビューして作成します。
- `/documents/`
  下書き保存、送信、再送信、承認フローを確認します。

## ローカル開発

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
$env:PYTHONPATH = 'app'
python -m uvicorn hoiku_plan_writer.main:app --reload
```

## Ollama で annual preview を試す

```powershell
$env:PYTHONPATH = 'app'
$env:HOIKU_PLAN_AI_ENABLE_ANNUAL_PREVIEW = 'true'
$env:HOIKU_PLAN_AI_PROVIDER = 'ollama'
$env:HOIKU_PLAN_AI_MODEL = 'qwen2.5:0.5b'
$env:HOIKU_PLAN_AI_BASE_URL = 'http://127.0.0.1:11434'
$env:HOIKU_PLAN_AI_TIMEOUT_SECONDS = '180'
python -m uvicorn hoiku_plan_writer.main:app --reload
```

既定の `qwen2.5:0.5b` は CPU-only でも比較的軽く、公開デモ向けの annual preview で使いやすい設定です。品質を上げたいときは `qwen2.5:1.5b` に切り替えて比較できます。

## 公開デモ

公開デモは `open-hoikuict` と同じ考え方で、セッション単位に分離した SQLite を使います。

- `PUBLIC_DEMO_MODE=1` で有効化します。
- ブラウザごとに初期データ入りのセッション DB を払い出します。
- ブラウザを閉じるか、画面の「このセッションを初期化」でデータをリセットできます。
- Dockge / Cloudflare Tunnel 用の構成は [DEPLOYMENT.md](DEPLOYMENT.md) と [compose.yaml](compose.yaml) にまとめています。

## テスト

```powershell
$env:PYTHONPATH = 'app'
C:\python\open-hoikuict\venv\Scripts\python.exe -m unittest discover -s tests
```

## 設計メモ

- ADR は `docs/adr/` にあります。
- 公開デモのセッション分離方針は `docs/adr/0005-public-demo-session-runtime.md` に整理しています。
- LLM は `app/hoiku_plan_writer/ai/` 配下で境界を切り、失敗時は既存 generator にフォールバックします。