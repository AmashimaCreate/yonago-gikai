# Data Schema

このディレクトリ配下のデータは、鳥取県内5議会を同じ形で扱うための共通スキーマに従う。

## councils.json

リポジトリ直下の `councils.json` は、対応対象の議会レジストリである。

必須キー:

- `id`: `yonago-city` のような一意なID
- `name`: 表示名
- `type`: `prefecture` または `city`
- `minutes_system`: `dbsr` / `kensakusystem` / `unknown`
- `vote_granularity`: `member` / `faction` / `result_only` / `unknown`
- `status`: `active` / `planned`

## members.json

配置: `docs/data/{council_id}/members.json`

```json
{
  "council_id": "yonago-city",
  "updated_at": "2026-06-11T00:00:00+00:00",
  "source_url": "https://www.city.yonago.lg.jp/2919.htm",
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
      "photo_url": "https://... or null"
    }
  ]
}
```

必須キー:

- ルート: `council_id`, `updated_at`, `source_url`, `members`
- 各議員: `id`, `council_id`, `name`, `name_kana`, `faction`, `elected_count`, `positions`, `committees`, `photo_url`

ルール:

- `id` は `{council_id}--{slug}` 形式。
- `positions` と `committees` は文字列配列。
- `photo_url` はURL文字列または `null`。

## votes.json

配置: `docs/data/{council_id}/votes.json`

このフェーズでは定義のみ。データ生成は次フェーズ以降。

```json
{
  "council_id": "yonago-city",
  "updated_at": "2026-06-11T00:00:00+00:00",
  "votes": [
    {
      "id": "yonago-city--令和8年3月定例会--bill-slug",
      "council_id": "yonago-city",
      "session": "令和8年3月定例会",
      "bill_title": "議案第1号 ...",
      "date": "2026-03-25",
      "result": "可決",
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

- `granularity` は `member` / `faction` / `result_only`。
- `granularity` が `member` 以外の場合、`votes_by_member` は `null`。
- `date` は `YYYY-MM-DD` または `null`。

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
  "speeches": [
    {
      "id": "yonago-city--2026-03-10--0001",
      "member_id": "yonago-city--adachi-takashi",
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

- ルート: `council_id`, `updated_at`, `speeches`
- 各発言: `id`, `member_id`, `meeting_name`, `date`, `kind`, `summary`, `source_url`

ルール:

- `member_id` は `{council_id}--{slug}`、または議員特定不能時は `null`。
- `summary` はAI要約が未生成の場合 `null`。
