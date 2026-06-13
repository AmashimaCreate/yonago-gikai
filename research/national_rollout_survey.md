# 全国展開・県議会データモデル偵察

調査日: 2026-06-13  
範囲: 実装なし。現行データモデルの47都道府県展開案と、県議会議員名簿の公式サイト様式サンプリング。  
書き込み範囲: `research/national_rollout_survey.md`

## サマリー

- 現行の `councils.json` と `docs/data/{council_id}/` 構造は、47都道府県議会へそのまま水平展開できる。最小変更は `type: "prefecture"` の議会を47件に増やし、各県に `members.json` / `profile.json` / `timeseries.json` を置く方式。
- 鳥取だけ「県+4市」まで存在する非対称は、全国トップでは「都道府県議会47件」を主導線にし、鳥取県ページ内に「市議会も掲載あり」として子議会を出すのが自然。47県すべてに市議会があるようには見せない。
- 議員名簿は5県サンプルだけでも、静的HTML個別ページ型、CMS一覧表型、Excel/PDF併用型、外部ASP型、地区別HTML分割型に分かれる。47県展開では少なくとも4から5種類の名簿アダプタと、少数の手動補正が必要になる見込み。
- 全国展開の初期目標は「氏名・会派・選挙区・期数/当選回数・写真URL・公式プロフィールURL」までを標準項目にするのが現実的。役職・委員会は取得可能性が高いが、表記の揺れが大きいため任意項目に留める。

## A. 現行モデルの47都道府県拡張

### 現行モデルの整理

`councils.json` は現在、次の5議会を同列の council として持つ。

| council_id | type | lg_code | 備考 |
|---|---:|---:|---|
| `tottori-pref` | `prefecture` | `310000` | 鳥取県議会 |
| `tottori-city` | `city` | `312011` | 鳥取市議会 |
| `yonago-city` | `city` | `312029` | 米子市議会 |
| `kurayoshi-city` | `city` | `312037` | 倉吉市議会 |
| `sakaiminato-city` | `city` | `312045` | 境港市議会 |

各 council は `id` / `name` / `type` / `prefecture` / `prefecture_name` / `lg_code` / `minutes_system` / `vote_granularity` / `official_links` / `status` を基本に持つ。県議会と市議会は同じ `council_id` 名前空間で扱われ、表示側も `docs/data/{council_id}/` を読む。

`docs/data/{council_id}/` の主要ファイルは次の形。

| ファイル | 47県展開での扱い |
|---|---|
| `members.json` | 県議会名簿の主要対象。全国展開の最初の実装対象にしやすい。 |
| `profile.json` | `lg_code` 単位の基礎指標。都道府県47件ならSSDS等で揃えやすい。 |
| `timeseries.json` | 県単位の人口・出生・財政力指数・県議選投票率などは比較的揃う。 |
| `speeches.json` | 会議録システム差が大きく、47県同時展開の初期対象から外すのが妥当。 |
| `votes.json` | 議決結果の公開形式差が大きく、初期は任意カバレッジ扱いが妥当。 |

### 47都道府県の council 設計案

最小変更案:

- 47都道府県をすべて `type: "prefecture"` の council として追加する。
- IDは既存の `tottori-pref` を維持し、他県も `{prefecture_slug}-pref` に揃える。
- `prefecture` は都道府県コード、`lg_code` は都道府県の地方公共団体コードを使う。
- 市議会データがある場合だけ、同じ `prefecture` を持つ `type: "city"` council としてぶら下げる。`parent_id` を追加しなくても `prefecture` で関連付けできるが、将来のUIでは `parent_council_id: "tottori-pref"` を追加すると明示的になる。

推奨する表示上の整理:

- 全国トップ: 「47都道府県議会」を主対象にする。地図の各都道府県から県議会ページへ遷移。
- 県ページ: 県議会データを主表示し、掲載済み市議会がある県だけ「この県内の市議会」枠を出す。
- 鳥取県: `tottori-pref` ページに `tottori-city` / `yonago-city` / `kurayoshi-city` / `sakaiminato-city` への導線を出す。鳥取だけ詳細化されていることを「先行掲載」として扱い、全国の市議会網羅と誤認させない。
- くらべる: 初期は都道府県議会47件のみの比較軸を追加し、市議会比較は現行鳥取県内比較として分ける。

### 全国トップの日本地図導線

既に47都道府県SVGがある前提なら、地図クリックは次の段階に分けるのが安全。

1. 地図の都道府県パスに `prefecture_code` または `slug` を持たせる。
2. 対応する `type: "prefecture"` council を `councils.json` から引く。
3. データがある県は県議会ページへ遷移し、未整備県は「準備中」状態を明示する。

ルーティング設計は、現行がハッシュルーティングで動くなら `#/prefectures/tottori-pref` または既存 council ルート流用で十分。将来 `seiji-mieru.com/tottori/` のようなパス配下に移す場合も、データfetchを相対パスまたはbase-awareにしておけば大きな問題はない。

## B. 県議会議員名簿の様式サンプリング

### サンプル結果

| 県 | 公式名簿URL | 形式 | 機械可読性 | 取得できる主項目 | robots確認 | アダプタ分類 |
|---|---|---|---|---|---|---|
| 東京都 | https://www.gikai.metro.tokyo.lg.jp/membership/ | 静的HTML。五十音順・選挙区別・会派別の一覧から個別HTMLへ遷移。 | 高い。HTMLリンクと個別プロフィール表を通常のHTMLパースで取得可能。 | 氏名、会派、期数、所属委員会、連絡先、選挙区、サイト、写真URL。 | `robots.txt` あり。`/membership/*.html` は禁止なし。ただし `/img/membership/` はDisallowのため写真画像のクロール保存は避け、URL参照に留めるのが安全。 | 静的HTMLリスト+個別HTML |
| 大阪府 | https://www.pref.osaka.lg.jp/gikai/giinjouhou/index.html | 議員情報トップから、議員連絡先一覧のPDF版・Excel版、会派別一覧、委員会別一覧等へ分岐。 | 高い。Excel版があり、名簿基礎項目は機械取得しやすい。HTML本文はリンク集中心。 | Excel/PDFで連絡先一覧。会派別、所属委員会別、会派構成も別ページ。写真は「議員すがたみ」等の別資料確認が必要。 | `https://www.pref.osaka.lg.jp/robots.txt` は404。禁止ルールなしとして扱うが、サイト負荷配慮は必要。 | Excel/PDF併用+補助HTML |
| 島根県 | https://www.pref.shimane.lg.jp/gikai/gaido/meibo/ | 名簿トップはPDFリンク中心。選挙区別HTMLから地区別HTML、個別HTMLへ遷移。 | 中から高。地区別HTMLを巡回すれば個別プロフィールに到達可能。 | 個別HTMLで写真、氏名、選挙区、当選回数、所属会派、所属委員会。選挙区定数は画像掲載あり。 | `https://www.pref.shimane.lg.jp/robots.txt` は404。禁止ルールなしとして扱うが、Imperva/CDN配下なので低頻度取得が無難。 | 地区別HTML分割+個別HTML |
| 岩手県 | https://www.pref.iwate.jp/gikai/giin/index.html | 県議会トップは公式CMS。実名簿は公式導線先の外部ASP `iwatekengikai.gijiroku.com`。 | 中。HTML表だがShift_JIS/CP932系。外部ASPのURL・文字コード対応が必要。 | 一覧で氏名、ふりがな、選挙区、所属会派、メール、ホームページ、住所、電話、写真。個別で所属委員会も取得可能。期数/当選回数は確認ページ上では見当たらない。 | `pref.iwate.jp/robots.txt` は `/cgi-*` のみDisallow。ASP側 `iwatekengikai.gijiroku.com/robots.txt` は一部botを禁止し、一般User-agentは `/voices/cgi/` 等を禁止。名簿ASP自体は禁止なし。 | 外部ASP HTML |
| 熊本県 | https://www.pref.kumamoto.jp/site/gikai/list3-11.html | CMSの一覧ページ。全議員名簿HTML表と個別ページ。PDF名簿も併用。 | 高い。集約HTML表で基礎項目が揃い、個別HTMLで写真・委員会等を補完可能。 | 一覧で氏名、フリガナ、選挙区、会派、期数。個別で写真、生年月日、所属委員会等。 | `robots.txt` あり。`Allow: /`。サイトマップあり。 | CMS一覧表+個別HTML |

### 確認URL

| 県 | 確認したURL |
|---|---|
| 東京都 | 名簿トップ: https://www.gikai.metro.tokyo.lg.jp/membership/ / 五十音順: https://www.gikai.metro.tokyo.lg.jp/membership/japanese-syllabary.html / 個別例: https://www.gikai.metro.tokyo.lg.jp/membership/num026.html / robots: https://www.gikai.metro.tokyo.lg.jp/robots.txt |
| 大阪府 | 議員情報: https://www.pref.osaka.lg.jp/gikai/giinjouhou/index.html / 議員連絡先一覧: https://www.pref.osaka.lg.jp/o170010/gikai_giji/giininfo/renrakusaki.html / Excel例: https://www.pref.osaka.lg.jp/documents/84154/giinnichirann080529.xls / robots確認: https://www.pref.osaka.lg.jp/robots.txt |
| 島根県 | 名簿トップ: https://www.pref.shimane.lg.jp/gikai/gaido/meibo/ / 選挙区別: https://www.pref.shimane.lg.jp/gikai/gaido/meibo/tiku.html / 地区例: https://www.pref.shimane.lg.jp/gikai/gaido/meibo/matsue.html / 個別例: https://www.pref.shimane.lg.jp/gikai/gaido/meibo/simeibetu/giin33_fukuda.html / robots確認: https://www.pref.shimane.lg.jp/robots.txt |
| 岩手県 | 公式導線: https://www.pref.iwate.jp/gikai/giin/index.html / 外部ASP一覧: https://iwatekengikai.gijiroku.com/g07_giinlistP.asp / 外部ASP個別例: https://iwatekengikai.gijiroku.com/g07_giinlistS.asp?SrchID=28 / 県robots: https://www.pref.iwate.jp/robots.txt / ASP robots: https://iwatekengikai.gijiroku.com/robots.txt |
| 熊本県 | 議員紹介: https://www.pref.kumamoto.jp/site/gikai/list3-11.html / 全議員名簿: https://www.pref.kumamoto.jp/site/gikai/51858.html / 個別例: https://www.pref.kumamoto.jp/site/gikai/8023.html / robots: https://www.pref.kumamoto.jp/robots.txt |

### 観察したアダプタパターン

1. 静的HTMLリスト+個別HTML

東京都が該当。構造が安定していれば最も扱いやすい。リストの会派略称を個別ページの正式会派で上書きする方がよい。

2. CMS一覧表+個別HTML

熊本県が該当。全議員HTML表に基礎項目がまとまっており、個別ページで写真・委員会を補う。全国展開の理想形に近い。

3. 地区別HTML分割+個別HTML

島根県が該当。選挙区別ページから複数地区ページを辿る必要がある。件数検算を「名簿PDFの議員数」または「議員名別PDF」と突き合わせる運用が必要。

4. Excel/PDF併用

大阪府が該当。Excelがあれば基礎名簿は安定取得できるが、写真や委員会は別HTML/別資料から補完する可能性がある。PDFのみの県では手動確認またはPDFパーサが必要。

5. 外部ASP HTML

岩手県が該当。公式サイトから外部ASPへリンクされる。文字コード、クエリURL、robots、ASP側の障害を個別に扱う必要がある。会議録ASPと同じベンダー配下なら他県にも横展開できる可能性がある。

## 全国展開の難易度見立て

### 取得項目ごとの現実性

| 項目 | 47県展開見込み | 備考 |
|---|---|---|
| 氏名 | 高 | ほぼ全県で取得可能と見てよい。 |
| 会派 | 高 | 表記揺れは大きいが、取得自体は可能性が高い。 |
| 選挙区 | 高 | 県議会名簿の基本項目。地区別ページだけの県では補完が必要。 |
| 期数/当選回数 | 中 | 熊本・東京・島根は確認可能。岩手サンプルでは確認できず。県により欠落を許容する必要がある。 |
| 写真 | 中 | HTMLにある県は多いが、東京都のようにrobotsで画像パスがDisallowの場合は画像保存せずURL参照に留める判断が必要。 |
| 役職 | 中 | 議長・副議長・委員長などは別ページや委員会欄に混ざる。正規化は後回しがよい。 |
| 所属委員会 | 中から高 | 個別ページや委員会別名簿で取れる例が多いが、表記の粒度差が大きい。 |

### 47県の実装方針案

初期フェーズ:

- 各県に `members_source` を定義し、`adapter_type` を明示する。
- 必須項目は `name` / `district` / `faction` / `source_profile_url` に絞る。
- `elected_count` / `photo_url` / `positions` / `committees` は取得できた場合だけ入れる。
- 写真は原則としてURL参照にし、画像ファイルの再配布・保存は県ごとの利用条件とrobotsを確認してからにする。
- robotsが404の自治体は「明示禁止なし」だが、巡回頻度を低くし、名簿更新時期に手動または年数回で取得する。

推奨するアダプタ構成:

| adapter_type | 対象例 | 実装難度 | 備考 |
|---|---|---:|---|
| `static_member_pages` | 東京都 | 低 | リンク抽出+個別table抽出。 |
| `cms_member_table` | 熊本県 | 低 | 集約表+個別補完。 |
| `district_split_pages` | 島根県 | 中 | 地区ページ巡回と件数検算が必要。 |
| `excel_roster` | 大阪府 | 中 | Excel解析は安定。写真や委員会補完は別アダプタ。 |
| `external_gijiroku_asp` | 岩手県 | 中 | 文字コードとASP URLルール対応が必要。 |
| `pdf_roster_manual_review` | PDFのみの県向け | 高 | 自動化できても検算・目視確認を残すべき。 |

5県サンプル時点の見積もり:

- 47県すべての「氏名・会派・選挙区」取得は現実的。
- 47県すべての「写真・期数・委員会」まで完全自動で揃えるのは、県ごとの欠落やrobots制約があるため初期目標にしない方がよい。
- アダプタは最低5種類、PDFのみや画像多用ページを考えると6から7種類を想定する。
- 本番運用では「県別アダプタ+共通正規化+件数検算」の形が妥当。完全汎用スクレイパではなく、県ごとの小さな設定ファイルを持つ方が保守しやすい。

## 鳥取の非対称性をどう扱うか

鳥取は既に県議会と4市議会があるため、全国展開後も「県議会47件」と「市議会先行掲載」を分けて見せるのがよい。

推奨:

- 全国地図は都道府県ページにだけリンクする。
- 鳥取県ページに「県内の掲載済み市議会」として4市を表示する。
- 県比較では県議会だけを並べる。
- 市議会比較は鳥取県内限定または「掲載済み自治体」比較として別軸にする。
- `councils.json` 上は特殊な親子テーブルを急いで追加せず、既存の `prefecture` / `type` でグルーピングする。必要になった段階で `parent_council_id` や `coverage_level` を追加する。

## 落とし穴

- robotsでHTMLは許容されていても、写真ディレクトリだけ禁止される例がある。東京都は `/img/membership/` がDisallowなので、写真の保存・再配布は避ける判断が必要。
- 議員名簿は更新日がページ単位で異なる。個別ページだけ更新される県では、一覧と個別の更新日差分を許容する必要がある。
- 会派名は略称と正式名称が混在する。保存時は `faction` を公式表記、必要なら `faction_short` を別管理する。
- 期数、当選回数、任期開始日のどれを出すかは県ごとに違う。数値化できない場合は欠落を許容する。
- 外部ASP型は公式導線であってもドメインが異なるため、robotsと文字コード、障害時のリトライ方針を別管理する。
- PDF/Excel併用型は、Excelが毎回同じURLとは限らない。リンク抽出から最新添付ファイルを見つける処理が必要。

## 推奨結論

全国展開は、まず47都道府県議会の `members.json` を対象にするのが現実的。`profile.json` / `timeseries.json` はSSDS等で県単位なら揃いやすいが、議会サイト固有の価値は議員名簿にある。

初期スコープは「氏名・会派・選挙区・期数/当選回数・写真URL・公式プロフィールURL」まで。委員会・役職は取れる県だけ任意で入れ、全国一律表示では欠落時の空欄を許容する。アダプタは5種類程度から始め、PDFのみの県を手動確認付きにするのが、47県を破綻なく進める現実的なルート。
