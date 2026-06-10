import { el } from "./utils.js";

export function acquisitionText(membersMeta) {
  const acquisition = membersMeta?.acquisition;
  if (acquisition === "scraping") {
    return "公式サイトから自動取得";
  }
  if (acquisition === "manual_transcription") {
    const date = confirmedDate(membersMeta);
    return `公式名簿を手作業で転記（確認日: ${date || "不明"}）`;
  }
  return "取得方法の記録がありません";
}

export function coverageText(speechesMeta, council = null) {
  if (!speechesMeta) {
    if (council?.minutes_system === "dbsr") {
      return "発言インデックス未取得（会議録が別システムのため）。";
    }
    return "発言インデックスはまだ取得していません。";
  }
  return "本会議での議員の発言のみ。委員会・議長の進行・市長や職員の答弁は含みません。";
}

export function sourceLink(url, label = "公式情報を確認") {
  if (!url) return null;
  return el(
    "a",
    {
      href: url,
      target: "_blank",
      rel: "noopener",
    },
    label,
  );
}

export function dataQualityPanel({ membersMeta, speechesMeta, council }) {
  const rows = [
    qualityRow(
      "議員名簿",
      acquisitionText(membersMeta),
      sourceLink(membersMeta?.source_url, "名簿の出典"),
      membersMeta?.acquisition,
    ),
    qualityRow(
      "発言インデックス",
      coverageText(speechesMeta, council),
      sourceLink(firstSpeechSourceUrl(speechesMeta), "発言の確認はこちら"),
      speechesMeta ? "speaker1_only" : "not_collected",
    ),
    qualityRow(
      "議案への賛否",
      "このフェーズではまだ表示していません。",
      null,
      "not_implemented",
    ),
  ];

  return el("section", { class: "quality-panel", "aria-label": "データ品質" }, [
    el("h2", { class: "section-title" }, "データの見方"),
    el("div", { class: "quality-grid" }, rows),
  ]);
}

export function cautionNote() {
  return el("p", { class: "caution-note" },
    "発言数は役職（議長等）・当選時期・取得範囲により異なります。少ないことが活動の少なさを意味するものではありません。",
  );
}

function qualityRow(label, text, link, rawValue) {
  return el("div", { class: "quality-row", "data-quality": rawValue || "" }, [
    el("span", { class: "quality-label" }, label),
    el("span", { class: "quality-text", title: rawValue || "" }, text),
    link ? el("span", { class: "quality-link" }, link) : null,
  ]);
}

function firstSpeechSourceUrl(speechesMeta) {
  const speeches = speechesMeta?.speeches;
  if (!Array.isArray(speeches) || speeches.length === 0) return null;
  return speeches.find((speech) => speech.source_url)?.source_url || null;
}

function confirmedDate(membersMeta) {
  const note = membersMeta?.source_note || "";
  const match = note.match(/令和\s*(\d+)年\s*(\d+)月\s*(\d+)日/);
  if (match) {
    const year = 2018 + Number(match[1]);
    return [
      year,
      String(Number(match[2])).padStart(2, "0"),
      String(Number(match[3])).padStart(2, "0"),
    ].join("-");
  }
  if (membersMeta?.updated_at) {
    return membersMeta.updated_at.slice(0, 10);
  }
  return null;
}
