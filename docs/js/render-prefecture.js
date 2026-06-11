import { councilPath } from "./router.js";
import { renderPrefectureComparison } from "./render-prefecture-comparison.js";
import { el } from "./utils.js";

export function renderPrefecturePage(root, councils, prefecture = "tottori", summaries = []) {
  root.innerHTML = "";
  const prefectureCouncils = councils.filter((council) => council.prefecture === prefecture);
  const prefectureCouncil = prefectureCouncils.find((council) => council.type === "prefecture");
  const summaryByCouncilId = new Map(
    summaries.map((summary) => [summary.council.id, summary]),
  );
  const mapFrame = el("div", { class: "map-frame municipality-map-frame" }, [
    el("p", { class: "muted" }, "鳥取県の市町村地図を読み込み中..."),
  ]);
  const comparison = renderPrefectureComparison(summaries, prefecture);
  const mapPanel = el("div", { class: "prefecture-tab-panel", "data-pref-panel": "browse" }, [
    el("section", { class: "prefecture-map-panel" }, [
      el("div", { class: "prefecture-map-layout" }, [
        prefectureCouncil
          ? el("div", { class: "prefecture-assembly-wrap" }, [
              el("p", { class: "map-caption" }, "県全体を扱う議会"),
              renderCouncilCard(
                prefectureCouncil,
                prefecture,
                summaryByCouncilId.get(prefectureCouncil.id),
                { hideTypeLabel: true },
              ),
            ])
          : null,
        el("div", {}, [
          mapFrame,
          el("div", { class: "map-legend", "aria-label": "地図の凡例" }, [
            el("span", {}, [
              el("span", { class: "legend-swatch is-supported" }),
              "対応済み",
            ]),
            el("span", {}, [
              el("span", { class: "legend-swatch is-unsupported" }),
              "未対応",
            ]),
          ]),
          el(
            "p",
            { class: "muted" },
            "鳥取県内19市町村(4市+15町村、14町1村)のうち、色付きの4市は議会ページへ進めます。グレーの15町村は未対応です。",
          ),
        ]),
      ]),
    ]),
    el("section", { class: "council-card-section" }, [
      el("div", { class: "section-heading-row" }, [
        el("div", {}, [
          el("p", { class: "eyebrow" }, "対応中の議会"),
          el("h2", { class: "section-title" }, "議会カードから選ぶ"),
        ]),
      ]),
      el(
        "div",
        { class: "council-grid" },
        prefectureCouncils.map((council) =>
          renderCouncilCard(council, prefecture, summaryByCouncilId.get(council.id)),
        ),
      ),
    ]),
  ]);
  const comparisonPanel = el("div", {
    class: "prefecture-tab-panel",
    "data-pref-panel": "compare",
    hidden: "",
  }, comparison ? [comparison] : [
    el("p", { class: "empty-message" }, "比較に使うデータを読み込めませんでした。"),
  ]);

  root.appendChild(
    el("section", { class: "prefecture-hero page-card" }, [
      el("p", { class: "eyebrow" }, "鳥取県"),
      el("h2", { class: "section-title" }, "どの議会を見る？"),
      el(
        "p",
        {},
        "地図または議会カードから、鳥取県内5議会の公開データへ進めます。",
      ),
      renderPrefectureTabs(),
    ]),
  );

  root.appendChild(mapPanel);
  root.appendChild(comparisonPanel);
  setupPrefectureTabs(root);

  hydrateMunicipalityMap(mapFrame, prefecture);
}

function renderPrefectureTabs() {
  return el("div", { class: "prefecture-tabs", role: "tablist", "aria-label": "鳥取県ページの表示切り替え" }, [
    el("button", {
      type: "button",
      class: "prefecture-tab is-active",
      "data-pref-tab": "browse",
      role: "tab",
      "aria-selected": "true",
    }, "見る"),
    el("button", {
      type: "button",
      class: "prefecture-tab",
      "data-pref-tab": "compare",
      role: "tab",
      "aria-selected": "false",
    }, "くらべる"),
  ]);
}

function setupPrefectureTabs(root) {
  const tabs = root.querySelectorAll("[data-pref-tab]");
  const panels = root.querySelectorAll("[data-pref-panel]");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.prefTab;
      tabs.forEach((item) => {
        const active = item.dataset.prefTab === target;
        item.classList.toggle("is-active", active);
        item.setAttribute("aria-selected", active ? "true" : "false");
      });
      panels.forEach((panel) => {
        panel.hidden = panel.dataset.prefPanel !== target;
      });
    });
  });
}

function renderCouncilCard(council, prefecture, summary = null, options = {}) {
  const memberText = typeof summary?.memberCount === "number"
    ? `議員${summary.memberCount}人`
    : "議員数を確認中";
  const hideTypeLabel = options.hideTypeLabel || council.type === "prefecture";
  return el("article", { class: `council-card ${council.type === "prefecture" ? "is-prefecture" : "is-city"}` }, [
    hideTypeLabel ? null : el("div", { class: "card-eyebrow" }, councilTypeLabel(council)),
    el("h3", {}, council.name),
    el("p", { class: "muted" }, memberText),
    el("a", { class: "button-link", href: councilPath(prefecture, council.id) }, "議会ページを見る"),
  ]);
}

function councilTypeLabel(council) {
  return council.type === "prefecture" ? "県議会" : "市議会";
}

async function hydrateMunicipalityMap(container, prefecture) {
  try {
    const response = await fetch("assets/maps/tottori-municipalities.svg");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    container.innerHTML = await response.text();

    const svg = container.querySelector("svg");
    if (!svg) throw new Error("SVG root not found");
    svg.removeAttribute("width");
    svg.removeAttribute("height");

    container.querySelectorAll(".municipality").forEach((region) => {
      const name = region.dataset.name || "市町村";
      const councilId = region.dataset.councilId;
      if (!councilId) {
        region.setAttribute("aria-label", `${name}（未対応）`);
        region.setAttribute("aria-disabled", "true");
        return;
      }
      region.setAttribute("role", "link");
      region.setAttribute("tabindex", "0");
      region.setAttribute("aria-label", `${name}議会ページへ`);
      region.addEventListener("click", () => {
        window.location.href = councilPath(prefecture, councilId);
      });
      region.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        window.location.href = councilPath(prefecture, councilId);
      });
    });
  } catch (error) {
    console.warn("Failed to load Tottori municipality map", error);
    container.innerHTML = "";
    container.appendChild(
      el(
        "p",
        { class: "caution-note" },
        "市町村地図を読み込めませんでした。議会カード一覧から選択してください。",
      ),
    );
  }
}
