# 九州6県 県議会議員名簿 様式調査

調査日: 2026-06-14  
対象: 福岡県・佐賀県・長崎県・大分県・宮崎県・鹿児島県  
対象外: 熊本県は実装済み、沖縄県は九州扱いをKT確認中のため未調査

## 結論

熊本県議会で作った `members_cms_table.py` をそのまま流用できる県は、今回の6県にはない。

ただし、6県は完全にバラバラではなく、次の3系統に分けられる。

| 系統 | 県 | 見立て |
| --- | --- | --- |
| 一覧 + 個別プロフィール型 | 福岡・宮崎・鹿児島 | 新規の `static_member_profile` 系アダプタで共通化できる可能性が高い。個別ページの許可リストパースが前提。 |
| 地区別/選挙区別の集約ページ型 | 長崎・大分 | 個別URLが議員単位ではなく選挙区/地区単位になる。`district_aggregate_profile` 系の新規アダプタが必要。 |
| 1ページWYSIWYG表型 | 佐賀 | 名簿1ページ内に写真・氏名・会派・期数・選挙区が埋め込まれる。単独の専用パーサが安全。 |

実装順としては、横展開効果が大きい **福岡・宮崎・鹿児島の「一覧 + 個別プロフィール型」** から着手するのがよい。既存の熊本アダプタを拡張して無理に吸収するより、`members_cms_table.py` は熊本型として残し、別に `members_static_profile.py` を作る方が破綻しにくい。

## サマリーマトリクス

| 県 | 名簿URL | 様式分類 | 取得可能項目 | robots / 写真制約 | 熊本アダプタ流用 |
| --- | --- | --- | --- | --- | --- |
| 福岡 | https://www.gikai.pref.fukuoka.lg.jp/site/giin/all.html | 静的HTML一覧 + 個別プロフィール | 氏名、ふりがな、会派、選挙区、当選回数、写真URL、公式プロフィールURL、委員会 | `Disallow: /giin/` あり。ただし現行名簿は `/site/giin/` 配下で明示禁止外。写真も同配下で禁止は確認されず。 | そのままは不可。個別プロフィール追跡型の新アダプタ向き。 |
| 佐賀 | https://www.pref.saga.lg.jp/gikai/kiji00366725/index.html | 1ページWYSIWYG表型 / 地区別ブロック | 氏名、ふりがな、会派、選挙区、当選回数、写真URL | robots.txt は404で明示禁止なし。写真は同ページ相対画像で禁止確認なし。 | 不可。WYSIWYG表の専用パースが必要。 |
| 長崎 | https://www.pref.nagasaki.jp/gikai/2010.html | 50音一覧 + 選挙区別集約ページ | 氏名、会派、選挙区、当選回数、写真URL、委員会。公式プロフィールURLは議員単位でなく選挙区ページ単位。 | `/kana/`, `/mobile/`, `/translate/` のみDisallow。`/gikai/` と画像は明示禁止なし。 | 不可。選挙区集約ページ型の新アダプタが必要。 |
| 大分 | https://www.pref.oita.jp/site/gikai/giin-gisekijun.html | 議席順HTML表 + 選挙区別集約ページ | 氏名、ふりがな、会派、選挙区、当選回数。写真URLは選挙区ページで取得可。公式プロフィールURLは選挙区ページ単位。 | robots.txt は404で明示禁止なし。写真は明示禁止確認なし。 | 一覧表部分は近いが、写真が選挙区ページ側なのでそのままは不可。 |
| 宮崎 | https://www.pref.miyazaki.lg.jp/gikai/about/members/50on/index.html | 静的HTML一覧 + 個別プロフィール | 氏名、ふりがな、会派、選挙区、当選回数、写真URL、公式プロフィールURL、委員会 | robotsは一部 `/documents/...` のみDisallow。名簿・写真は禁止確認なし。 | そのままは不可。福岡・鹿児島と同じ新アダプタ候補。 |
| 鹿児島 | https://www.pref.kagoshima.jp/aa02/gikai/giin/profile/index.html | 写真グリッド + 個別プロフィール / PDF名簿併設 | 氏名、ふりがな、会派、選挙区、当選回数、写真URL、公式プロフィールURL、委員会 | `/kojisotatsu/` のみDisallow。名簿・写真は禁止確認なし。 | そのままは不可。福岡・宮崎と同じ新アダプタ候補。 |

## 県別詳細

### 福岡県議会

- 公式入口: https://www.gikai.pref.fukuoka.lg.jp/
- 議員紹介: https://www.gikai.pref.fukuoka.lg.jp/site/giin/index.html
- 全議員一覧: https://www.gikai.pref.fukuoka.lg.jp/site/giin/all.html
- 個別プロフィール例: https://www.gikai.pref.fukuoka.lg.jp/site/giin/akita-syouji.html
- 様式:
  - 議員紹介トップに選挙区別・会派別・委員会別・全議員一覧への導線。
  - 全議員一覧は氏名リンク + 会派の表。
  - 個別ページに写真、選挙区、会派、当選回数、委員会等。
- 取得可能:
  - 一覧: 氏名、ふりがな、会派、公式プロフィールURL。
  - 個別: 写真URL、選挙区、当選回数、委員会。
- 注意:
  - 個別ページには生年月日、住所、電話、FAXも掲載されているため、実装時は許可リスト方式で必要項目だけ読む。
  - robots.txt は `/giin/` と `/m/giin/` をDisallowしているが、現行名簿は `/site/giin/` 配下。
- アダプタ見立て:
  - 熊本のCMS表型では不足。`static_member_profile` 型の有力候補。

### 佐賀県議会

- 公式入口: https://www.pref.saga.lg.jp/gikai/
- 議員一覧: https://www.pref.saga.lg.jp/gikai/kiji00366725/index.html
- 様式:
  - 1ページに選挙区/地区ごとのブロックが並ぶ。
  - 各ブロック内に写真行とテキスト行が対応するWYSIWYG表。
  - 画像はリンクではなく、個別プロフィールページは確認できない。
- 取得可能:
  - 氏名、ふりがな、会派、選挙区、当選回数、写真URL。
  - 公式プロフィールURLは議員単位では存在しないため `null` が妥当。
- robots:
  - `https://www.pref.saga.lg.jp/robots.txt` は404。明示的な禁止は確認できず。
  - 写真は名簿ページ相対の画像ファイルで、別ディレクトリDisallowは確認できず。
- アダプタ見立て:
  - 熊本型の流用不可。
  - WYSIWYG表の構造が崩れやすいため、まずは佐賀専用に近い `saga_wysiwyg_roster` として書き、他県に同型が出たら抽象化するのが安全。

### 長崎県議会

- 公式入口: https://www.pref.nagasaki.jp/gikai/
- 議員名簿（50音順）: https://www.pref.nagasaki.jp/gikai/2010.html
- 会派別議員名簿: https://www.pref.nagasaki.jp/gikai/2020.html
- 選挙区ページ例: https://www.pref.nagasaki.jp/gikai/2010-01.html
- 様式:
  - 50音順一覧は氏名リンクのリスト。
  - リンク先は議員単独ページではなく、選挙区ごとに複数議員をまとめたページ。
  - 会派は会派別ページにもまとまっている。
- 取得可能:
  - 選挙区ページ: 氏名、写真URL、選挙区、当選回数、会派、委員会。
  - 公式プロフィールURLは議員単位ではなく、同じ選挙区ページURLを複数議員で共有する形になる。
- 注意:
  - 選挙区ページには住所・電話などの連絡先が混在する。許可リスト方式必須。
- robots:
  - `/kana/`, `/mobile/`, `/translate/` はDisallow。
  - `/gikai/` は明示禁止外。写真ディレクトリの禁止も確認できず。
- アダプタ見立て:
  - 熊本型の流用不可。
  - `district_aggregate_profile` 型が必要。

### 大分県議会

- 公式入口: https://www.pref.oita.jp/site/gikai/
- 議員名簿入口: https://www.pref.oita.jp/site/gikai/list22228.html
- 議席順議員名簿: https://www.pref.oita.jp/site/gikai/giin-gisekijun.html
- 選挙区ページ例: https://www.pref.oita.jp/site/gikai/giin-usuki.html
- 様式:
  - 議席順名簿はHTML表で、氏名リンク・ふりがな・会派・当選回数・選挙区が揃う。
  - 氏名リンクの先は、議員単独ではなく選挙区別ページ。複数議員が同居する選挙区がある。
  - 選挙区ページに顔写真とプロフィール情報がある。
- 取得可能:
  - 議席順表: 氏名、ふりがな、会派、当選回数、選挙区。
  - 選挙区ページ: 写真URL、補助的な会派・当選回数。
  - 公式プロフィールURLは選挙区ページ単位。
- 注意:
  - 選挙区ページには住所・電話・FAX等の連絡先があるため、写真等だけを許可リストで取得する。
- robots:
  - `https://www.pref.oita.jp/robots.txt` は404。明示的な禁止は確認できず。
- アダプタ見立て:
  - 一覧表だけなら熊本型に近いが、写真取得には選挙区ページが必要。
  - `members_cms_table.py` の単純流用ではなく、表 + 集約ページ追跡の新アダプタが適切。

### 宮崎県議会

- 公式入口: https://www.pref.miyazaki.lg.jp/gikai/
- 五十音順名簿: https://www.pref.miyazaki.lg.jp/gikai/about/members/50on/index.html
- 個別プロフィール例: https://www.pref.miyazaki.lg.jp/gikai/about/members/50on/aragami_minoru.html
- 様式:
  - 50音順・会派別・委員会別・選挙区別の導線あり。
  - 50音順ページは写真/氏名リンクの一覧。
  - 個別プロフィールページに詳細表。
- 取得可能:
  - 一覧/個別: 氏名、ふりがな、会派、選挙区、当選回数、写真URL、公式プロフィールURL、委員会。
- 注意:
  - 個別ページには生年月日、年齢、住所、電話、FAX、メールがある。収集対象外として明示的にスキップする。
- robots:
  - 一部 `/documents/...` のみDisallow。名簿配下は禁止確認なし。
  - 写真ディレクトリの明示的なDisallowも確認できず。
- アダプタ見立て:
  - 福岡・鹿児島と同じ `static_member_profile` 型候補。

### 鹿児島県議会

- 公式入口: https://www.pref.kagoshima.jp/gikai/
- 議員紹介: https://www.pref.kagoshima.jp/gikai/giin/index.html
- PDF名簿: https://www.pref.kagoshima.jp/aa02/gikai/giin/giinnmeibo/index.html
- 議員一覧（写真グリッド）: https://www.pref.kagoshima.jp/aa02/gikai/giin/profile/index.html
- 個別プロフィール例: https://www.pref.kagoshima.jp/ha01/gikai/giin/profile/hisai.html
- 様式:
  - 議員紹介トップに、PDF名簿・議員一覧・選挙区別・会派別・当選回数別への導線。
  - 議員一覧は写真グリッド。写真クリックで個別プロフィールへ。
  - PDF名簿も併設されているが、HTML個別ページから主要項目は取得可能。
- 取得可能:
  - 一覧/個別: 氏名、ふりがな、会派、選挙区、当選回数、写真URL、公式プロフィールURL、委員会。
- 注意:
  - 個別プロフィールには生年月日、連絡先住所、電話、FAX、政治姿勢、コメントが含まれる。収集対象は許可リストに限定する。
  - 氏名の正確表記ページが別にあるため、異体字確認が必要なら補助ソースとして使える。
- robots:
  - `/kojisotatsu/` のみDisallow。名簿・プロフィール・写真は禁止確認なし。
- アダプタ見立て:
  - 福岡・宮崎と同じ `static_member_profile` 型候補。

## 実装方針案

### 1. `static_member_profile` 型を先に作る

対象: 福岡・宮崎・鹿児島

共通処理:

- 一覧ページからプロフィールURL一覧を抽出。
- 個別プロフィールページを取得。
- 許可リストで以下のみ読む。
  - 氏名
  - ふりがな
  - 会派
  - 選挙区
  - 当選回数
  - 写真URL
  - 委員会
  - 公式プロフィールURL
- 生年月日、年齢、住所、電話、FAX、メール、政治姿勢、コメントは読まない。

県ごとの差:

- 福岡は全議員一覧の表に会派があり、個別ページで選挙区・当選回数・写真。
- 宮崎は一覧と個別の両方に情報がある。
- 鹿児島は写真グリッドから個別ページを辿る。

### 2. `district_aggregate_profile` 型を別で作る

対象: 長崎・大分

共通処理:

- 一覧/表から基本項目を取り、リンク先の選挙区ページを補助的に読む。
- 1ページに複数議員がいるため、氏名でページ内の該当ブロックを同定する。
- 公式プロフィールURLは議員単位ではなく選挙区ページURLになる可能性があるため、フロント表示では「公式ページを見る」程度にする。

### 3. 佐賀は専用パーサから始める

対象: 佐賀

理由:

- 1ページ内のWYSIWYG表で、写真行とテキスト行の対応関係を復元する必要がある。
- 個別プロフィールURLがない。
- 県内の選挙区ブロックを読むだけなのでリクエスト負荷は低い。

## 追加メモ

- 九州6県のうち、連絡先等の個人情報が個別ページに混在する県が多い。実装時は既存方針どおり、ページ全体から自動抽出するのではなく、許可リスト方式で必要項目だけを読む。
- 写真URLは、今回の確認範囲では6県とも名簿・プロフィール配下に明示的なrobots禁止は確認されなかった。ただし、実装直前に各県robots.txtを再確認する。
- 全国展開の観点では、「CMS表型だけで多数県をカバーできる」というより、「表型」「静的個別プロフィール型」「選挙区集約型」「WYSIWYG表型」の4類型を持つとかなり広がりそう。
