# hoiku-plan-writer

`open-hoikuict` から独立公開する、保育計画文書作成アプリです。将来の本体統合を前提に、設計思想は継承しつつ、文書作成ドメインだけを独立した bounded context として切り出しています。

## 継承しているもの

- `FastAPI + SQLModel + Jinja2 + HTMX`
- サーバ中心の画面構成
- role ベース権限制御
- 本体統合しやすい参照契約

## 継承しないもの

- 既存業務モデルへの直接依存
- 本体 DB への密結合
- 単一 DB 前提の外部キー設計

## 現状

- `open-hoikuict` 継承方針を ADR 化
- 園プロファイル、年間指導計画、月案、レビューの初期 Web 画面を追加
- 文書をセクション単位で保持する SQLModel 永続化を追加
- `nursery_ref / classroom_ref / actor_ref` ベースの境界設計を追加
- CLI のサンプル生成も維持

## ディレクトリ

```text
C:\python\hoiku-plan-writer
|- app\hoiku_plan_writer\
|  |- auth.py
|  |- db.py
|  |- main.py
|  |- domain\
|  |- persistence\
|  |- services\
|  |- templates\
|  `- web\
|- docs\
|  `- adr\
|- tests\
|- pyproject.toml
`- README.md
```

## セットアップ

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
```

## 起動

```powershell
uvicorn hoiku_plan_writer.main:app --reload
```

または

```powershell
hoiku-plan-server
```

## 主な画面

- `/staff/login`
  モック職員ログイン。role / nursery_ref / classroom_refs を切り替えられます。
- `/nursery-profile/`
  園プロファイルの保存と有効化
- `/annual-plans/new`
  年間指導計画のプレビューと下書き保存
- `/monthly-plans/new`
  月案のプレビューと下書き保存
- `/documents/`
  文書一覧とレビュー

## テスト

標準ライブラリのテスト:

```powershell
$env:PYTHONPATH = "app"
python -m unittest discover -s tests
```

この作業では、依存が入っている参照元仮想環境を使って以下を確認しました。

```powershell
$env:PYTHONPATH = "app"
C:\python\open-hoikuict\venv\Scripts\python.exe -m unittest discover -s tests
```

## 設計メモ

- ADR は `docs/adr/` に配置
- `section_key` と `source_refs` は将来統合向けの安定契約として扱う
- 文書ブロックは DB 上でも独立行として保持し、将来の部分再生成や差分保存に備える
