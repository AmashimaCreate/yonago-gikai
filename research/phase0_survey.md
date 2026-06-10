# Phase 0 Survey Notes

## 2026-06-11 追記: Phase 3 前提確認

### 鳥取3市の会議録検索入口

Phase 0時点では鳥取3市を `ssp.kaigiroku.net` 系としていたが、公式導線を再確認した結果、少なくとも米子市・倉吉市の正式入口は `www.kensakusystem.jp` 旧系統だった。境港市は公式議会ページがHTTP 500を返しており、公式ページから会議録検索リンクまでは到達できなかったが、`www.kensakusystem.jp/sakaiminato/` の会議録検索トップは稼働している。

| 議会 | 公式導線 | 確認できた会議録入口 | 入口系統 | robots判定 | Phase 3 実装判断 |
|---|---|---|---|---|---|
| 米子市議会 | `https://www.city.yonago.lg.jp/gikai/` → `https://www.city.yonago.lg.jp/2924.htm` | `https://www.kensakusystem.jp/yonago-s/index.html` | kensakusystem legacy | 米子市公式 `robots.txt` は404。`www.kensakusystem.jp/robots.txt` も404。 | 実装可。正式入口は `yonago-s`。`https://www.kensakusystem.jp/yonago/` も200だが公式リンクではないため補助扱い。 |
| 倉吉市議会 | `https://www.city.kurayoshi.lg.jp/gyousei/div/gikai/` | `http://www.kensakusystem.jp/kurayoshi/`（HTTPSも200確認） | kensakusystem legacy | 倉吉市公式 `robots.txt` は404。`www.kensakusystem.jp/robots.txt` も404。 | 実装可。 |
| 境港市議会 | 市トップに `./index.php?view=20` の議会リンクあり。ただし当該ページは2026-06-11確認時点でHTTP 500。 | 公式導線からは未確定。稼働確認済み入口は `https://www.kensakusystem.jp/sakaiminato/` | kensakusystem legacy（暫定） | 境港市公式 `robots.txt`: `ChatGPT-User` / `GPTBot` 等は許可、`User-agent: *` は `Crawl-delay: 5` かつ `Disallow: /`。`www.kensakusystem.jp/robots.txt` は404。 | ベンダー入口の実装は可能。ただし「公式ページからの正式リンク」は公式ページ復旧後に再確認する。境港市公式サイト自体の自動取得は現行 `CouncilScraperBase` UAでは不可。 |

補足:

- `ssp.kaigiroku.net/tenant/yonago/`, `yonago-s/`, `kurayoshi/`, `sakaiminato/` は軽いHEAD確認でタイムアウトし、鳥取3市の新系統併設は確認できなかった。
- したがって Phase 3 の鳥取3市会議録アダプタは `kensakusystem_legacy` として扱うのが妥当。
- `www.kensakusystem.jp` 旧系統は、トップHTMLから `cgi-bin3/See.exe?Code=...` と `cgi-bin3/Search2.exe?Code=...&sTarget=2` を抽出する方式になる。
- `www.kensakusystem.jp` 旧系統はHTMLレスポンスだけでなく検索POST本文もCP932でURLエンコードする必要がある。UTF-8で送信すると日本語の発言者名がCGI側で文字化けし、検索結果が0件になる。全国のlegacy系展開時も、検索語・発言者・会議日ラベルなど日本語パラメータはCP932送信を前提にする。

### 議員別賛否データの所在

| 議会 | 所在 | 形式 | 判断 |
|---|---|---|---|
| 鳥取県議会 | 公式サイト `https://www.pref.tottori.lg.jp/87621.htm` → 各定例会 → `議案等の議決結果`。例: `https://www.pref.tottori.lg.jp/326506.htm` | HTMLページ + PDF。ページ内に「議員別の賛否の状況」PDFリンクあり。 | DBSR内のみではなく、県公式CMS側で公開。 |
| 鳥取市議会 | 公式サイト `https://www.city.tottori.lg.jp/site/shigikai/list20-168.html` → `https://www.city.tottori.lg.jp/site/shigikai/6332.html` | PDF中心。平成26年6月定例会以降の賛否状況を公開。 | DBSR内のみではなく、市公式CMS側で公開。 |

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
| kensakusystem 新系統（鳥取3市では正式入口として未確認） | `ssp.kaigiroku.net` | `User-agent: *` は `Disallow: /`。ただし `/tenant/` は許可、`/tenant/js/`, `/tenant/css/`, `/tenant/help/`, `/tenant/stats/` は拒否。 | 鳥取3市の正式入口は今回確認できず。全国向け `kensakusystem_ssp` adapter 候補として別扱い。 |
| 米子・倉吉・境港 kensakusystem 旧系統 | `www.kensakusystem.jp` | `robots.txt` は404。 | 鳥取3市のPhase 3実装対象。トップHTMLから `cgi-bin3/See.exe` / `cgi-bin3/Search2.exe` の `Code` を抽出する。 |
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
