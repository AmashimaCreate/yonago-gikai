# Data Schema

このディレクトリ配下のデータは、鳥取県内5議会を同じ形で扱うための共通スキーマに従う。

## councils.json

リポジトリ直下の `councils.json` は、対応対象の議会レジストリである。

必須キー:

- `id`: `yonago-city` のような一意なID
- `name`: 表示名
- `type`: `prefecture` または `city`
- `prefecture`: URL階層用の都道府県slug。例: `tottori`
- `prefecture_name`: 都道府県の表示名。例: `鳥取県`
- `lg_code`: 総務省「全国地方公共団体コード」の6桁文字列
- `minutes_system`: `dbsr` / `kensakusystem` / `kensakusystem_legacy` / `unknown`
- `vote_granularity`: `member` / `faction` / `result_only` / `unknown`
- `status`: `active` / `planned`

任意キー:

- `minutes_base_url`: 会議録検索システムの議会別トップURL。
- `notes`: 自動取得や公式導線に関する補足。

ルール:

- `lg_code` は議会固有のコードではなく、議会が属する自治体の全国地方公共団体コードを記録する。
- `lg_code` は e-Stat、総務省決算カード、自治体基礎データとの機械的JOINキーとして使う。
- コード確認元: 総務省「全国地方公共団体コード」 https://www.soumu.go.jp/denshijiti/code.html

## members.json

配置: `docs/data/{council_id}/members.json`

```json
{
  "council_id": "yonago-city",
  "updated_at": "2026-06-11T00:00:00+00:00",
  "source_url": "https://www.city.yonago.lg.jp/2919.htm",
  "acquisition": "scraping",
  "members": [
    {
      "id": "yonago-city--adachi-takashi",
      "council_id": "yonago-city",
      "name": "安達 卓是",
      "name_kana": "あだち たかし",
      "faction": "信風",
      "elected_count": 3,
      "positions": ["総務政策副委員長"],
      "committees": ["総務政策", "基地問題等調査特別"],
      "photo_url": "https://... or null",
      "official_profile_url": "https://... or null"
    }
  ]
}
```

必須キー:

- ルート: `council_id`, `updated_at`, `source_url`, `acquisition`, `members`
- 各議員: `id`, `council_id`, `name`, `name_kana`, `faction`, `elected_count`, `positions`, `committees`, `photo_url`

ルール:

- `acquisition` は `scraping` / `manual_transcription`。
- `id` は `{council_id}--{slug}` 形式。
- `positions` と `committees` は文字列配列。
- `photo_url` はURL文字列または `null`。
- 議員個別ページのパースは許可リスト方式とし、取得する項目を明示列挙する。
- 許可リスト外の項目は読まない。特に電話番号、メールアドレス、自宅住所、生年月日等の個人情報は、公式サイトに掲載されていても公開データへ取り込まない。

任意キー:

- `official_profile_url`: 議員本人の公式プロフィールページURL。URL文字列または `null`。値がある場合は、利用者が公式情報を自分で確認する動線としてフロントに表示する。

## manual members source

配置: `data_sources/members_manual/{council_id}.json`

robots.txt 等により自動取得しない議会の、人間転記用入力ファイル。

```json
{
  "council_id": "sakaiminato-city",
  "source_url": "https://...",
  "source_note": "KT が公式サイトの議員名簿ページを確認して転記",
  "members": [
    {
      "id": "sakaiminato-city--sample-taro",
      "council_id": "sakaiminato-city",
      "name": "境港 太郎",
      "name_kana": "さかいみなと たろう",
      "faction": null,
      "elected_count": null,
      "positions": [],
      "committees": [],
      "photo_url": null,
      "source_url": "https://..."
    }
  ]
}
```

ルール:

- ルートの `source_url` は転記元の議員名簿ページ。
- 各議員にも `source_url` を持たせる。個別ページがない場合はルートと同じ議員名簿ページURLを入れる。
- 生成される `docs/data/{council_id}/members.json` では、ルートに `acquisition: "manual_transcription"` を付与し、各議員の `source_url` は公開スキーマからは落とす。

## votes.json

配置: `docs/data/{council_id}/votes.json`

このフェーズでは定義のみ。データ生成は次フェーズ以降。

```json
{
  "council_id": "yonago-city",
  "updated_at": "2026-06-11T00:00:00+00:00",
  "acquisition": "scraping",
  "votes": [
    {
      "id": "yonago-city--令和8年3月定例会--bill-slug",
      "council_id": "yonago-city",
      "session": "令和8年3月定例会",
      "bill_title": "議案第1号 ...",
      "date": "2026-03-25",
      "result": "可決",
      "committee_report": null,
      "granularity": "member",
      "votes_by_member": [
        {"member_id": "yonago-city--adachi-takashi", "vote": "賛成"}
      ],
      "votes_by_faction": null,
      "source_url": "https://..."
    }
  ]
}
```

必須キー:

- ルート: `council_id`, `updated_at`, `votes`
- 各議決: `id`, `council_id`, `session`, `bill_title`, `date`, `result`, `granularity`, `votes_by_member`, `votes_by_faction`, `source_url`

ルール:

- `acquisition` は `scraping` / `manual_transcription` / `manual_download`。未付与の既存データも当面は許容するが、新規生成では来歴を明示する。
- `granularity` は `member` / `faction` / `result_only`。
- `granularity` が `member` 以外の場合、`votes_by_member` は `null`。
- `date` は `YYYY-MM-DD` または `null`。
- `committee_report` は任意。請願・陳情で委員長報告（採択 / 不採択 / 研究留保 等）がPDFにある場合のみ文字列で保持する。`bill_title` は件名セルのみとし、陳情事項本文や委員長報告を連結しない。
- `votes_by_member[].vote` は `賛成` / `反対` / `退席` / `欠席` / `議長` / `除斥` / `継続審査` のいずれか。
- `議長` は慣例により採決に加わらない議長席を表す。賛否の意思表示として扱わない。
- `除斥` は地方自治法上の利害関係等により議事から除かれた状態を表す。フロントでは「利害関係があるため採決から外れた状態」のように平易な注記を添える。
- `継続審査` はPDF上の `△` 等、議員セルに継続審査として記録された値を表す。結果欄の文言を議員セルへ混入させない。
- `votes_by_member[].member_name` は、`member_id` が `null` の場合もPDF上の投票者名を保持するためのフィールド。`speeches.json` の `speaker_label` と同じく、現名簿外の人物や表記揺れを後から確認できるように残す。

## profile source input

配置: `data_sources/profiles/{council_id}.json`

自治体基礎データの一次入力ファイル。人間が公式サイト、e-Stat、総務省決算カード等の一次ソースから確認・転記した値を正とし、ビルダーが検証と派生値計算を行う。

```json
{
  "council_id": "yonago-city",
  "population": {
    "value": 142472,
    "as_of": "2026-05-31",
    "source_name": "米子市 人口と世帯数（住民基本台帳）",
    "source_url": "https://www.city.yonago.lg.jp/9498.htm"
  },
  "households": null,
  "budget_general_yen": null,
  "fiscal_index": null,
  "aging_rate_pct": null,
  "local_debt_yen": null,
  "member_salary_monthly_yen": null
}
```

必須キー:

- ルート: `council_id`, `population`, `households`, `budget_general_yen`, `fiscal_index`, `aging_rate_pct`, `local_debt_yen`, `member_salary_monthly_yen`

ルール:

- 未調査・取得不能の項目は `null`。
- 値がある項目はオブジェクトとし、`value` と `source_url` を必須とする。
- `source_url` は `https://` で始まるURL。
- `population`, `households`, `budget_general_yen`, `local_debt_yen`, `member_salary_monthly_yen` は整数値。
- `fiscal_index`, `aging_rate_pct` は数値。
- `population` は `0` より大きい値。
- 時点を持つ項目は `as_of`、会計年度を持つ項目は `fiscal_year` を付ける。

## profile.json

配置: `docs/data/{council_id}/profile.json`

`data_sources/profiles/{council_id}.json` から生成される公開用データ。入力ファイルの内容に `per_capita` と `updated_at` を加える。

```json
{
  "council_id": "yonago-city",
  "population": {"value": 142472, "as_of": "2026-05-31", "source_url": "https://..."},
  "households": null,
  "budget_general_yen": null,
  "fiscal_index": null,
  "aging_rate_pct": null,
  "local_debt_yen": null,
  "member_salary_monthly_yen": null,
  "per_capita": {
    "population_per_member": 5479.7,
    "budget_per_capita_yen": 620894,
    "debt_per_capita_yen": 404290
  },
  "updated_at": "2026-06-11T00:00:00+00:00"
}
```

必須キー:

- ルート: `council_id`, `population`, `households`, `budget_general_yen`, `fiscal_index`, `aging_rate_pct`, `local_debt_yen`, `member_salary_monthly_yen`, `per_capita`, `updated_at`
- `per_capita`: `population_per_member`, `budget_per_capita_yen`, `debt_per_capita_yen`

派生値:

- `population_per_member`: 人口 ÷ 議員数。議員数は `docs/data/{council_id}/members.json` の `members` 件数から算出し、ファイルがない場合は `null`。
- `budget_per_capita_yen`: 一般会計予算 ÷ 人口。
- `debt_per_capita_yen`: 地方債残高 ÷ 人口。
- 必要な入力が `null` の場合、派生値は `null`。

## speeches.json

配置: `docs/data/{council_id}/speeches.json`

このフェーズでは定義のみ。データ生成は次フェーズ以降。

```json
{
  "council_id": "yonago-city",
  "updated_at": "2026-06-11T00:00:00+00:00",
  "coverage": {
    "scope": "本会議・議員発言者(speaker1)のみ",
    "excluded": ["議長の議事進行発言", "市長・執行部の発言(member_id: null扱い)"],
    "note": "議長は慣例により一般質問を行わないため発言数が少なく/ゼロに見える場合がある",
    "source_url_note": "個別発言への直接リンクは本システムの仕様上提供不可。source_url は会議録検索入口。"
  },
  "speeches": [
    {
      "id": "yonago-city--2026-03-10--0001",
      "member_id": "yonago-city--adachi-takashi",
      "speaker_label": "安達議員",
      "meeting_name": "令和8年3月定例会 本会議",
      "date": "2026-03-10",
      "kind": "一般質問",
      "summary": null,
      "source_url": "https://..."
    }
  ]
}
```

必須キー:

- ルート: `council_id`, `updated_at`, `coverage`, `speeches`
- `coverage`: `scope`, `excluded`, `note`, `source_url_note`
- 各発言: `id`, `member_id`, `speaker_label`, `meeting_name`, `date`, `kind`, `summary`, `source_url`

ルール:

- `member_id` は `{council_id}--{slug}`、または議員特定不能時は `null`。
- `speaker_label` は会議録検索システム上の発言者表記。`member_id` が `null` の場合も表記揺れや過去議員の検出に使うため保持する。
- `summary` はAI要約が未生成の場合 `null`。
- `coverage` は取得範囲と構造的な欠落を説明する。フロントエンドでは、議長や執行部の発言が対象外であることを表示に利用する。
- `source_url` は永続性を優先し、会議録検索入口URLを保存する。旧系統の `Code` 付き検索URLや `ResultFrame.exe` URLは直接リンクとして永続利用しない。
