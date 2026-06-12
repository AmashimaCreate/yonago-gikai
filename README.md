# 議会見える化

鳥取県内5議会の公開データを、市民が見つけやすい形に並べ直す非公式サイトです。

- 公開サイト: https://amashimacreate.github.io/tottori-mieru/
- 対象: 鳥取県議会、鳥取市議会、米子市議会、倉吉市議会、境港市議会
- フロントエンド: vanilla JS / CSS / 静的JSON
- 公開方式: GitHub Pages

## 目的

自治体や議会が公開している情報を、議員名簿、発言インデックス、議決結果、街の基礎データとして同じ形で見られるようにします。
評価や順位づけではなく、一次ソースへたどる入口を増やすことを目的にしています。

## データ更新

`.github/workflows/update.yml` で月1回の自動更新を実行します。

- 議員名簿: 各議会の公式名簿ページを取得し、構造化できる範囲をJSON化
- 発言インデックス: 会議録検索システムから、本会議での議員発言者・会議名・日付を取得
- 議決結果: 公式の議決結果ページまたはPDFから、議案名・議決日・結果・賛否を抽出
- 街の基礎データ: 自治体公式資料、決算カード、e-Stat 社会・人口統計体系から取得
- 検証: `scripts/validate.py`、`scripts/check_links.py`、`scripts/check_personal_info.py`

SSDS時系列データの更新には、GitHub Actions Secret `ESTAT_APP_ID` が必要です。

## 主要ファイル

- `docs/index.html`: GitHub Pages の入口
- `docs/js/`: 画面描画とルーティング
- `docs/data/`: 公開サイトが読み込むJSONデータ
- `scripts/`: データ生成・検証スクリプト
- `research/`: 調査メモ
- `VISION.md`: 設計思想とロードマップ
- `HANDOFF.md`: 開発引き継ぎ情報

## 出典・クレジット

- 議員名簿・議決結果・会議録: 各議会、各自治体、会議録検索システムの公開情報
- 統計データ: 政府統計の総合窓口(e-Stat) 社会・人口統計体系
- 日本地図: geolonia/japanese-prefectures (GFDL)
- 鳥取県市町村地図: 国土数値情報 行政区域データ (PDL1.0)

## 免責

このサイトは非公式・個人運営です。正確な情報は公式発表を優先してください。
