import { el } from "./utils.js?v=20260614-finance";

const PURPOSE_COLORS = [
  "#0072b2",
  "#e69f00",
  "#009e73",
  "#cc79a7",
  "#56b4e9",
  "#d55e00",
  "#785ef0",
  "#999999",
  "#117733",
  "#882255",
];

export function renderFinanceSection(finance) {
  if (!finance?.expenditure?.purpose?.items?.length) return null;

  const purpose = finance.expenditure.purpose;
  const nature = finance.expenditure.nature;
  const maxAmount = Math.max(...purpose.items.map((item) => item.amount_thousand_yen || 0));

  return el("section", { class: "finance-section page-card" }, [
    el("div", { class: "section-heading-row finance-heading" }, [
      el("div", {}, [
        el("p", { class: "eyebrow" }, "このまちのお金の使いみち"),
        el("h2", { class: "section-title" }, "決算で見る歳出内訳"),
      ]),
      el("span", { class: "finance-badge" }, `決算 / ${finance.fiscal_year}年度`),
    ]),
    el("p", { class: "finance-lead" }, [
      "予算は計画、決算は実際に使われたお金です。ここでは目的別の歳出を大きい順に並べています。",
    ]),
    finance.similar_group
      ? el("p", { class: "finance-peer-note" }, `類似団体平均との比較: ${finance.similar_group}`)
      : null,
    el("div", { class: "finance-total-row" }, [
      el("span", {}, "歳出合計"),
      el("strong", {}, formatOkuYen(purpose.total_thousand_yen)),
      el("small", {}, `人口 ${Number(finance.population?.value || 0).toLocaleString("ja-JP")}人で割った1人あたり額も併記`),
    ]),
    el("div", { class: "finance-bars" }, purpose.items.map((item, index) =>
      renderFinanceBar(item, maxAmount, index),
    )),
    el("p", { class: "finance-note" },
      "1人あたり額は歳出を人口で割った参考値です。国や県からのお金も含むため、市民の負担額ではありません。",
    ),
    nature?.items?.length
      ? el("details", { class: "finance-nature-details" }, [
          el("summary", {}, "性質別歳出（人件費・扶助費など）を見る"),
          el("div", { class: "finance-bars is-secondary" },
            nature.items.map((item, index) =>
              renderFinanceBar(
                item,
                Math.max(...nature.items.map((entry) => entry.amount_thousand_yen || 0)),
                index,
              ),
            ),
          ),
        ])
      : null,
    el("p", { class: "finance-source" }, [
      `出典: ${finance.source?.name || "地方財政データ"}（${finance.fiscal_year}年度決算）。`,
      `ライセンス: ${finance.source?.license || "出典表記が必要なオープンデータ"}。`,
      "予算は計画、決算は実績です。",
    ]),
  ]);
}

function renderFinanceBar(item, maxAmount, index) {
  const width = maxAmount > 0
    ? Math.max(2, (item.amount_thousand_yen / maxAmount) * 100)
    : 0;
  const color = PURPOSE_COLORS[index % PURPOSE_COLORS.length];
  const peer = item.similar_group_average_per_capita_yen;
  const peerN = item.similar_group_average_n;
  return el("article", { class: "finance-bar-row", style: `--bar-width: ${width}%; --bar-color: ${color};` }, [
    el("div", { class: "finance-bar-label" }, [
      el("strong", {}, item.label),
      el("span", {}, `${formatOkuYen(item.amount_thousand_yen)} / ${formatPercent(item.share_pct)}`),
    ]),
    el("div", { class: "finance-bar-track", "aria-hidden": "true" }, [
      el("span", { class: "finance-bar-fill" }),
    ]),
    el("div", { class: "finance-bar-meta" }, [
      el("span", {}, `1人あたり ${formatYenPerPerson(item.per_capita_yen)}`),
      peer != null
        ? el("span", {}, `類似団体平均 ${formatYenPerPerson(peer)}/人${formatPeerN(peerN)}`)
        : el("span", {}, "類似団体平均: データなし"),
    ]),
  ]);
}

function formatPeerN(value) {
  return typeof value === "number" ? `(${value}市平均)` : "";
}

function formatOkuYen(thousandYen) {
  if (typeof thousandYen !== "number") return "データなし";
  const oku = thousandYen / 100000;
  return `${oku.toLocaleString("ja-JP", {
    maximumFractionDigits: oku >= 100 ? 0 : 1,
  })}億円`;
}

function formatPercent(value) {
  if (typeof value !== "number") return "0%";
  return `${value.toLocaleString("ja-JP", { maximumFractionDigits: 1 })}%`;
}

function formatYenPerPerson(value) {
  if (typeof value !== "number") return "データなし";
  if (value >= 10000) {
    return `${(value / 10000).toLocaleString("ja-JP", { maximumFractionDigits: 1 })}万円`;
  }
  return `${Math.round(value).toLocaleString("ja-JP")}円`;
}
