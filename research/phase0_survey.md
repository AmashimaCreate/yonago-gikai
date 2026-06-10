# Phase 0 Survey Notes

## 2026-06-11 追記: robots.txt 実測

### 境港市公式サイト

- 対象: `https://www.city.sakaiminato.lg.jp/robots.txt`
- 結果:
  - `Googlebot`, `Bingbot`, `Slurp`, `Applebot`, `ChatGPT-User`, `GPTBot` は許可。
  - `User-agent: *` は `Crawl-delay: 5` かつ `Disallow: /`。
- 判断:
  - 本プロジェクトの `CouncilScraperBase` の UA は許可対象ではないため、境港市公式サイトの自動取得は行わない。
  - 境港市議会の議員一覧は `data_sources/members_manual/sakaiminato-city.json` への人間転記方式に切り替える。
  - 全国展開時の分類として「robots ブロック自治体」を設ける必要がある。

### 会議録ベンダードメイン

| 対象 | ドメイン | robots.txt 結果 | Phase 3/4 への示唆 |
|---|---|---|---|
| 米子・倉吉・境港 kensakusystem 系 | `ssp.kaigiroku.net` | `User-agent: *` は `Disallow: /`。ただし `/tenant/` は許可、`/tenant/js/`, `/tenant/css/`, `/tenant/help/`, `/tenant/stats/` は拒否。 | `/tenant/` 配下の許可範囲に限定した設計が必要。詳細検索結果や本文URLが許可範囲内か、Phase 3 着手時に個別確認する。 |
| 鳥取県議会 DBSR 系 | `www.pref.tottori.dbsr.jp` | `User-agent: *` は `Disallow: /`。`/$`, `/index.php$`, `/index.php/$` のみ許可。 | トップ/検索入口以外のクロールは不可扱い。会議録本文の機械収集は robots 上の制約が強い。 |
| 鳥取市議会 DBSR 系 | `www.city.tottori.tottori.dbsr.jp` | `User-agent: *` は `Disallow: /`。`/$`, `/index.php$`, `/index.php/$` のみ許可。 | 鳥取県議会と同様。DBSR 系は会議録本文クロール前提ではなく、許可された入口・公式ダウンロード・手動/許諾取得の検討が必要。 |

## Phase 2 議員一覧取得状況

| 議会 | 方式 | URL | 取得人数 | 取得できた項目 | 取得できない/未取得項目 |
|---|---|---|---:|---|---|
| 鳥取県議会 | scraping | `https://www.pref.tottori.lg.jp/75928.htm` | 35 | 氏名、ふりがな、会派、委員会 | 当選回数、写真、役職 |
| 鳥取市議会 | scraping | `https://www.city.tottori.lg.jp/site/shigikai/6355.html` | 32 | 氏名、ふりがな、会派、当選回数、委員会、写真 | 役職 |
| 米子市議会 | scraping | `https://www.city.yonago.lg.jp/2919.htm` | 26 | 氏名、ふりがな、会派、当選回数、委員会、写真、役職 | なし |
| 倉吉市議会 | scraping | `https://www.city.kurayoshi.lg.jp/4253.htm` | 17 | 氏名、ふりがな、会派、当選回数、委員会、写真、役職 | なし |
| 境港市議会 | manual_transcription | 未転記。KT が公式議員名簿ページを確認して `data_sources/members_manual/sakaiminato-city.json` に記録予定 | 未生成 | 手動転記後に確定 | robots.txt により Codex UA での自動取得不可 |

## 議員一覧パーサの共通化余地

- 鳥取県議会と倉吉市はどちらも i-SITE 系 CMS だが、議員一覧のHTML構造は大きく異なる。
  - 鳥取県議会: ブログ型エントリ + category link。
  - 倉吉市: 本文テキスト内の `議席番号` ブロック。
- 鳥取市は自治体CMSの表形式で、米子市も表形式だがセル構成と役職/委員会の表現が異なる。
- 現時点で安全に共通化できるのは、以下の小さな部品に留めるのが妥当。
  - ふりがなからローマ字 slug を作る処理。
  - URL正規化、重複ID付与、テキスト正規化。
  - members.json 保存時の `acquisition` 付与。
- 5議会のうち4議会は自動生成できたが、境港市のような robots ブロック自治体が存在するため、全国展開では「スクレイピングアダプタ」と「手動転記/許諾取得アダプタ」の併存が必要。
