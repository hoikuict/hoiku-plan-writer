# hoiku-plan-writer

保育園向けの保育計画文書作成アプリです。現時点では、MVP仕様書に沿って「園プロファイル」「年間指導計画」「月案」「レビュー可能な構造化出力」の土台を Python で整えています。

## 現状

- 仕様書に合わせたドメインモデルを追加
- 年間指導計画と月案の最小生成ロジックを追加
- 生成結果をセクション単位で保持する構造を追加
- CLI からサンプル生成を確認できる入口を追加
- 標準ライブラリで動く最小テストを追加

## ディレクトリ

```text
C:\python\hoiku-plan-writer
|- app\hoiku_plan_writer\      # アプリ本体
|- docs\                       # 仕様・設計メモ
|- tests\                      # テスト
|- pyproject.toml
`- README.md
```

## セットアップ

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
```

依存は最小限にしているので、初期段階では標準ライブラリ中心で動きます。

## 使い方

年間指導計画のサンプル出力:

```powershell
python -m hoiku_plan_writer demo-annual
```

月案のサンプル出力:

```powershell
python -m hoiku_plan_writer demo-monthly
```

セクションキー一覧:

```powershell
python -m hoiku_plan_writer section-keys
```

## テスト

```powershell
$env:PYTHONPATH = "app"
python -m unittest discover -s tests
```

## 次の実装候補

- Web UI またはフォーム UI の追加
- 下書き保存と版管理
- レビュー履歴と承認フロー
- AI 連携部分の実装
- PDF 向けレイアウト整備

