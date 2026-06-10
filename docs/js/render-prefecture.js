import { councilPath } from "./router.js";
import { el } from "./utils.js";

export function renderPrefecturePage(root, councils, prefecture = "tottori") {
  root.innerHTML = "";
  root.appendChild(
    el("section", { class: "intro-panel" }, [
      el("h2", { class: "section-title" }, "鳥取県内5議会"),
      el(
        "p",
        {},
        "公開されている議員名簿・基礎データ・会議録発言インデックスを、議会ごとに同じ形で確認できます。",
      ),
    ]),
  );

  root.appendChild(
    el(
      "div",
      { class: "council-grid" },
      councils.map((council) => renderCouncilCard(council, prefecture)),
    ),
  );
}

function renderCouncilCard(council, prefecture) {
  return el("article", { class: `council-card ${council.type === "prefecture" ? "is-prefecture" : "is-city"}` }, [
    el("div", { class: "card-eyebrow" }, councilTypeLabel(council)),
    el("h3", {}, council.name),
    el("p", { class: "muted" }, readableMinutesSystem(council.minutes_system)),
    el("a", { class: "button-link", href: councilPath(prefecture, council.id) }, "議会ページを見る"),
  ]);
}

function readableMinutesSystem(value) {
  if (value === "kensakusystem_legacy") return "会議録検索システムから発言インデックスを取得済み";
  if (value === "dbsr") return "会議録は別システムのため発言インデックス未取得";
  return "会議録の取得方式を調査中";
}

function councilTypeLabel(council) {
  return council.type === "prefecture" ? "県議会" : "市議会";
}
