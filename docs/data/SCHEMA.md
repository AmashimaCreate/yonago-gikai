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
