# 引き継ぎドキュメント (HANDOFF.md)

このプロジェクトは、これまで VS Code + Claude Code で開発されてきました。
2026年4月末より OpenAI Codex に開発環境を移行します。

このドキュメントは、Codex がプロジェクトの現状・規約・次の作業を
即座に理解するための引き継ぎ文書です。

## プロジェクト概要

- **名称**: 米子市政の見える化サイト(yonago-gikai)
- **目的**: 米子市民が市政情報に簡単にアクセスできるようにする
- **公開URL**: https://amashimacreate.github.io/yonago-gikai/
- **リポジトリ**: https://github.com/amashimacreate/yonago-gikai
- **設計思想**: 詳細は VISION.md を参照

## 開発履歴に関する注意

GitHubユーザーネームを KGguitar から amashimacreate に変更しました。
過去のコミット履歴やドキュメントに古いユーザーネームが残っている可能性
がありますが、これはユーザー変更前の記録です。

GitHubは旧URLを新URLに自動リダイレクトしますが、可能な限り
新しいユーザーネーム amashimacreate を使用してください。

## 現在の達成状況(2026年4月末時点)

### 完了済み

- Phase 1: 議員データベース(26名)
  - 4ビュー(会派・委員会・役職・当選回数)
  - 検索/フィルタ
  - 議員SNS・公式HPリンク(26人分手動収集済み)
  - GitHub Actions による月1回自動更新
  - GitHub Pages 公開

- Phase 2.1: 新着情報タイムライン
  - 市政情報の新着(info)
  - 市民意見募集(iken)
  - カテゴリフィルタ + キーワード検索
  - GitHub Actions による週1回自動更新

- VISION.md による設計思想の明文化
- ES Modules へのリファクタリング(app.js を 6ファイルに分割)

### 進行中

- Phase 2.2: 議会活動データ
  - 計画は立てたが未着手
  - 次の作業として「Phase 2.2.1: 質問項目PDFインデックス」を予定

## ディレクトリ構成

- yonago-gikai/
  - README.md (プロジェクト紹介)
  - VISION.md (設計思想・ロードマップ)
  - HANDOFF.md (この引き継ぎドキュメント)
  - .github/workflows/
    - update.yml (議員データの月1自動更新)
    - update_news.yml (新着データの週1自動更新)
  - scripts/
    - scrape.py (議員データのスクレイピング)
    - scrape_news.py (新着データのスクレイピング)
    - sync_links.py (議員IDと手動リンクの整合性チェック)
  - docs/ (GitHub Pages 配信ルート)
    - index.html
    - css/style.css
    - js/ (ES Modules 構成)
      - main.js (起動・タブ切替・データ読み込み)
      - state.js (アプリケーション状態)
      - utils.js (共通DOM ヘルパー)
      - search.js (検索・フィルタロジック)
      - render-members.js (議員ビュー描画)
      - render-news.js (新着ビュー描画)
    - data/
      - members.json (議員データ - 自動生成)
      - member_links.json (議員SNS/HPリンク - 手動メンテ)
      - news.json (新着データ - 自動生成)

## 技術スタック

- **スクレイピング**: Python 3.12 + requests + BeautifulSoup4
- **フロントエンド**: vanilla JavaScript (ES Modules) + HTML + CSS
- **データ**: JSON ファイル(リポジトリ管理)
- **公開**: GitHub Pages
- **自動更新**: GitHub Actions
- **フレームワーク**: 不使用(VISION.md の方針)
- **ビルド工程**: なし(直接ブラウザで実行可能)

## 開発時の規約(重要)

### 1. データの分離
- 自動生成データ(members.json、news.json): スクレイピングで生成
- 手動メンテナンスデータ(member_links.json): 人間が編集
- この2種類を1つのファイルに混ぜない

### 2. ファイル設計
- ES Modules で機能別に分割
- 1ファイル300行を目安に
- 循環インポートを避ける(タブ間連携は CustomEvent 経由)
- import パスは相対パス、大文字小文字を厳密に守る

### 3. 段階的進行
- Phase ごとに動くものを完成させてから次へ
- 各サブフェーズで動作確認を必ず行う
- 過剰な機能追加は避ける(最小変更スタイル)

### 4. スクレイピングのマナー
- User-Agent を設定
- time.sleep(2) 等で適切な間隔を空ける
- robots.txt を尊重
- 最低件数チェック(0件で異常終了)

### 5. コミット規約
- プレフィックス使用: feat / fix / refactor / docs / chore など
- タイトル50字以内
- 本文に「なぜ」と「動作確認」を明記

## ローカル開発手順

### 環境セットアップ
- cd yonago-gikai
- python3 -m venv .venv
- source .venv/bin/activate
- pip install requests beautifulsoup4

### ローカルサーバー起動(必須)
ES Modules を使っているため、ファイル直接開きでは動かない。
必ずローカルサーバー経由で確認すること。

- cd docs
- python3 -m http.server 8765

その後ブラウザで http://localhost:8765/ を開く。

### スクレイピング実行
- .venv/bin/python scripts/scrape.py
- .venv/bin/python scripts/scrape_news.py
- .venv/bin/python scripts/sync_links.py

## GitHub Actions の動作

- update.yml: 毎月1日 09:30 JST に scrape.py + sync_links.py を実行
- update_news.yml: 毎週月曜 09:15 JST に scrape_news.py を実行
- どちらも workflow_dispatch で手動実行可能
- 失敗時に Issue 自動作成

## 次に着手する作業

### Phase 2.2.1: 質問項目PDFインデックス

**目的**: 議会の質問項目PDFを一覧化するインデックスを作る

**データソース**:
- https://www.city.yonago.lg.jp/13691.htm (質問項目一覧)

**スコープ**:
- HTMLから「定例会名・日付・PDFファイル名・PDFサイズ」を抽出
- docs/data/assembly_archive.json として保存
- 新タブ「議会活動」を追加

**サブフェーズ案**:
1. scrape_assembly.py で 13691.htm を取得 → JSON 生成
2. 「議会活動」タブ追加 + 一覧UI
3. 13764.htm(議決結果)を追加
4. 検索・フィルタ機能
5. GitHub Actions で自動更新

**設計上の留意点**:
- VISION.md の「人軸」(将来の議員プロフィール統合)につながる土台として作る
- データ構造に member_id フィールドを置ける余地を残す
- HTML パースで完結、PDF パースは Phase 3 で別途

## Phase 3 以降の構想

- Phase 3: PDF処理基盤
  - 質問項目PDFの中身抽出 → 議員別データへ
  - 議決結果PDFの中身抽出 → 議案別データへ
  - 予算書・決算書PDF → 数値の可視化
- Phase 4: 議員プロフィール統合(人軸の本格実装)
- Phase 5: AI活用検討
  - 参考: デジタル庁「源内」OSS、国会議員マップ(kokkaimap.jp)
  - Claude Haiku で発言要約等

## 参考にした先行事例

### 国会議員マップ
- URL: https://kokkaimap.jp/
- 国政レベルで同様のことを実現している個人プロジェクト
- AI要約に Claude Haiku 4.5 を使用
- 真似する要素: 個別議員ページ、テーマ別ビュー、ニュース解説
- 米子の独自性: 市議会レベルの身近さ、委員会活動、市政の数字

### デジタル庁「源内」OSS
- URL: https://www.digital.go.jp/policies/genai
- GitHub: https://github.com/digital-go-jp/genai-web, /genai-ai-api
- 行政向けRAGの実装テンプレートとして参考
- MIT ライセンスで商用利用可能

## 開発者の好み・スタイル

### 1. 段階的・確認重視
- 大規模な変更を一気にやらない
- 各ステップで動作確認してから次へ
- 「実装案を提案 → 合意 → 実装」の流れを期待

### 2. 最小変更スタイル
- 機能を盛り込まず、必要最小限から始める
- 過剰な装飾・ライブラリを避ける
- 「これは必要か?」を都度問い直す

### 3. 設計判断の事前確認
- 実装前にデータ構造案・命名規約を確認する習慣がある
- 「OK なら実装します」の流れを好む

### 4. 命名は日本語OK
- コミットメッセージは英語プレフィックス + 日本語本文
- データの「カテゴリ名」「ラベル」は日本語

### 5. ファイル整理を重視
- リファクタリングを早めに行う
- ファイル分割の判断を早く下す

## Codex への第一プロンプトの推奨

Codex を初めて起動する時、以下を投げると即座に状況把握できます:

「このリポジトリは VS Code + Claude Code で開発されてきた米子市政の
見える化サイトです。HANDOFF.md と VISION.md を読んで、現在の状況を
把握してください。その後、次に着手予定の Phase 2.2.1: 質問項目PDF
インデックスの実装案を提案してください。実装に入る前に、データ構造案と
サブフェーズ案を確認したいです。」

## 既知の課題・引き継ぎ事項

1. member_links.json の最新性: 議員のSNS/HPは時間とともに変動する可能性あり、半年ごとに見直し推奨
2. 米子市公式ページの構造変化リスク: スクレイピング先のHTML構造が変わった場合、scrape.py の対応が必要
3. 過去ドキュメントに残る旧ユーザーネーム: KGguitar が一部のコミットメッセージや過去ファイルに残っている可能性

## 連絡先・運営情報

- 開発者: KT (GitHub: amashimacreate)
- プロジェクトは公開、MIT ライセンスを想定(LICENSE ファイルは未作成)
