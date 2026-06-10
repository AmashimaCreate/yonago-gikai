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
- `www.kensakusystem.jp` 旧系統の発言者プルダウンには、CP932の拡張領域で複数の符号化候補を持つ異体字が含まれる場合がある。米子市の `岩﨑議員` はHTML raw value上の `﨑` が `fa b1` だが、Unicode文字列として再エンコードすると `ed 95` になり、CGI検索が0件になる。発言者検索ではプルダウン `value` のraw bytesを保持し、そのままフォーム送信する必要がある。
- `ResultFrame.exe` の復元URLは素のGETでframesetまでは返るが、個別発言への永続的な直接リンクとしては扱いにくい。`speeches.json` の `source_url` は `Code` を焼き込まず、各tenantの静的検索入口 `index.html` にフォールバックする。

### Phase 3 kensakusystem legacy 実測

米子・倉吉・境港の3市は、`minutes_base_url` のtenant差し替えのみで同一アダプタを実行できた。自治体固有の分岐・個別コードは不要だった。

| 議会 | tenant | speaker1候補 | speeches件数 | member_id紐付け | 0件speaker | 補足 |
|---|---|---:|---:|---:|---|---|
| 米子市議会 | `yonago-s` | 26 | 286 | 286/286（100.0%） | なし | `岩﨑議員` はraw value送信により6件取得。 |
| 倉吉市議会 | `kurayoshi` | 23 | 290 | 231/290（79.7%） | なし | 未照合6名は現行 `members.json` にいない過去議員。現職17名は全員紐付けあり。 |
| 境港市議会 | `sakaiminato` | 14 | 190 | 0/190（0.0%） | なし | `members.json` 未生成のため全件 `member_id: null`。議員名簿の手動転記後に再照合可能。 |

共通化所見:

- `index.html` から `Search2.exe?Code=...` を抽出する構造、`speaker1` プルダウン、年タブ `changeyear(...)`、検索結果の `Javascript:go('context')` は3市で共通。
- 差があったのは発言者valueの表記だけ。米子は「姓+議員」、倉吉・境港はフルネームだが、プルダウンvalueを正として扱えば自治体固有対応なしで吸収できる。
- `source_url` は3市とも `https://www.kensakusystem.jp/{tenant}/index.html` の静的入口を保存する。

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

## 2026-06-11 追記: 議員個別プロフィール・追加項目所在調査

調査範囲:

- 実装は行わず、公式サイト上の所在と取得可能性のみ確認。
- `scripts/` は読み取りのみ。編集なし。
- 対象は、Phase 2時点で不足している鳥取県議会の当選回数・役職・写真、鳥取市議会の役職を中心に確認。

### サマリー

| 議会 | 個別公式プロフィールページ | URLパターン | 追加で取れる項目 | 取得に必要な追加リクエスト見積もり |
|---|---|---|---|---:|
| 鳥取県議会 | あり | `https://www.pref.tottori.lg.jp/item/{item_id}.htm#itemid{item_id}` | 写真、期数（当選回数相当）、所属会派、所属委員会等 | 全員写真まで取るなら35件。委員長等の役職は別途 `322790.htm` 1件、議長・副議長は `75926.htm` / `75927.htm` の2件。合計で既存一覧に加えて最大38件程度。 |
| 鳥取市議会 | なし（議員個別ページは確認できず） | 氏名セルにリンクなし。議席順・会派別・委員会別の一覧ページ構成 | 役職は議長・副議長ページと各委員会ページで取得可能 | 既存議席順に加え、議長・副議長1件、委員会一覧1件、委員会詳細7件程度。合計追加9件程度。 |
| 米子市議会 | なし（Phase 2時点の議員一覧テーブル内に個別リンクなし） | なし | Phase 2時点で必要項目は一覧から取得済み | 追加不要 |
| 倉吉市議会 | なし（1ページ内の議席番号セクション） | なし | Phase 2時点で必要項目は一覧から取得済み | 追加不要 |
| 境港市議会 | 未確認 | 境港市公式サイトは `User-agent: *` で `Disallow: /` のため Codex UA では確認しない | KT手動転記後に判断 | 自動取得なし |

### 鳥取県議会

#### 議員個別ページ

議員名簿 `https://www.pref.tottori.lg.jp/75928.htm` の各氏名リンクから、35人全員の個別ページに遷移できる。

例:

- 市谷知子: `https://www.pref.tottori.lg.jp/item/1165907.htm#itemid1165907`
- 伊藤保: `https://www.pref.tottori.lg.jp/item/1125474.htm#itemid1125474`
- 入江誠: `https://www.pref.tottori.lg.jp/item/967688.htm#itemid967688`

市谷知子ページで確認できた構造:

- 写真: `/secure/1165907/01ichitani_thumb.jpg`
- 所属会派: `無所属`
- 所属委員会等: `農林水産商工常任委員会`
- 期数: `5`
- 生年月日、自宅住所、自宅電話番号、事務所住所等も同じ表にあるが、本プロジェクトでは取得対象外にすべき個人情報が含まれる。

判断:

- `elected_count` は個別ページの `期数` から取得可能。
- `photo_url` は個別ページの `secure/{item_id}/...jpg` から取得可能。
- 個人住所・電話等を同じ表から誤取得しないよう、パーサでは許可リスト方式で `期数` と写真だけ拾うのが安全。

#### 役職

議長・副議長:

- 議長: `https://www.pref.tottori.lg.jp/75926.htm`
  - 例: `第89代鳥取県議会議長　福田　俊史`
  - 写真: `/secure/1165938/89gichou-r.jpg`
- 副議長: `https://www.pref.tottori.lg.jp/75927.htm`
  - 例: `第83代鳥取県議会副議長　浜田　一哉`
  - 写真: `/secure/1166004/83fukugichou.jpg`

委員長・副委員長:

- 委員会別名簿: `https://www.pref.tottori.lg.jp/322790.htm`
- 表構造は `役職`, `氏名`, `所属会派`, `期数`, `選挙区`。
- 各委員会表で `委員長` / `副委員長` / `委員` が明示される。

見積もり:

- 既存の議員名簿1件に加えて、個別ページ35件、委員会別名簿1件、議長・副議長2件。
- 全項目を自動取得する場合、合計追加38リクエスト程度。
- 2秒間隔では追加取得だけで最低76秒程度。

### 鳥取市議会

#### 議員個別ページ

議席順ページ `https://www.city.tottori.lg.jp/site/shigikai/6355.html` の氏名セルにはリンクがない。

確認した関連ページ:

- 議席順: `https://www.city.tottori.lg.jp/site/shigikai/6355.html`
- 会派別: `https://www.city.tottori.lg.jp/site/shigikai/6353.html`
- 委員会別: `https://www.city.tottori.lg.jp/site/shigikai/6336.html`

判断:

- 鳥取市議会は、議員個別プロフィールページではなく、一覧ページ群で情報を公開している構造。
- 既存の議席順ページから写真・当選回数・会派・所属委員会は取得済み。

#### 役職

議長・副議長:

- `https://www.city.tottori.lg.jp/site/shigikai/6372.html`
- `議長・副議長の役割` と `正副議長あいさつ` のページ。
- 例:
  - `第66代議長` 星見健蔵
  - `第65代副議長` 長坂則翁
- 写真も同ページにあるが、既存の議席順ページで写真は取得済み。

委員長・副委員長:

- 委員会別インデックス: `https://www.city.tottori.lg.jp/site/shigikai/6336.html`
- そこから各委員会ページへリンク。
- 代表例: 総務企画委員会 `https://www.city.tottori.lg.jp/page/6369.html`
  - 表の氏名セルで `委員長 吉野 恭介`、`副委員長 伊藤 幾子` のように明示。

委員会詳細ページ候補:

- 総務企画委員会: `/page/6369.html`
- 福祉保健委員会: `/page/6366.html`
- 文教経済委員会: `/page/6367.html`
- 建設水道委員会: `/page/6352.html`
- 議会運営委員会: `/page/6368.html`
- 議会広報広聴委員会: `/page/6354.html`
- 議会改革検討委員会: `/page/6340.html`

見積もり:

- 既存の議席順ページに加えて、議長・副議長ページ1件、委員会別インデックス1件、委員会詳細7件。
- 役職を完全に取る場合、追加9リクエスト程度。
- 2秒間隔では追加取得だけで最低18秒程度。
