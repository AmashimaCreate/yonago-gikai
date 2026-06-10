import { councilPath } from "./router.js";
import { el } from "./utils.js";

const ENABLED_COUNCILS = new Set(["yonago-city"]);

export function renderTop(root, councils) {
  root.innerHTML = "";
  root.appendChild(
    el("section", { class: "intro-panel" }, [
      el("h2", { class: "section-title" }, "鳥取県内5議会"),
      el(
        "p",
        {},
        "公開されている議員名簿・基礎データ・会議録発言インデックスを、議会ごとに同じ形で確認できます。",
      ),
      el(
        "p",
        { class: "muted" },
        "まず米子市議会ページで新しい画面構成を確認中です。他の議会ページは次段階で展開します。",
      ),
    ]),
  );

  root.appendChild(
    el(
      "div",
      { class: "council-grid" },
      councils.map((council) => renderCouncilCard(council)),
    ),
  );

  root.appendChild(
    el("section", { class: "disclaimer-panel" }, [
      el("h2", { class: "section-title" }, "利用にあたって"),
      el("p", {}, "このサイトは非公式・個人運営です。正確な情報は各議会・自治体の公式発表を優先してください。"),
      el("p", {}, "公開情報の見える化を目的としています。議員や関係者への嫌がらせ、威圧、差別的な利用を禁じます。"),
      el("p", {}, "発言件数によるランキングや序列化は行いません。発言数は役職・当選時期・取得範囲で変わります。"),
    ]),
  );
}

function renderCouncilCard(council) {
  const enabled = ENABLED_COUNCILS.has(council.id);
  const action = enabled
    ? el("a", { class: "button-link", href: councilPath(council.id) }, "議会ページを見る")
    : el("span", { class: "button-link is-disabled" }, "次段階で展開");

  return el("article", { class: "council-card" }, [
    el("div", { class: "card-eyebrow" }, council.type === "prefecture" ? "県議会" : "市議会"),
    el("h3", {}, council.name),
    el("p", { class: "muted" }, readableMinutesSystem(council.minutes_system)),
    action,
  ]);
}

function readableMinutesSystem(value) {
  if (value === "kensakusystem_legacy") return "会議録検索システムから発言インデックスを取得済み";
  if (value === "dbsr") return "会議録は別方式のため次フェーズ以降に対応";
  return "会議録の取得方式を調査中";
}
