import { councilPath } from "./router.js";
import { renderPrefectureComparison } from "./render-prefecture-comparison.js";
import { el } from "./utils.js";

export function renderPrefecturePage(root, councils, prefecture = "tottori", summaries = []) {
  root.innerHTML = "";
  const prefectureCouncil = councils.find((council) => council.type === "prefecture");
  const mapFrame = el("div", { class: "map-frame municipality-map-frame" }, [
    el("p", { class: "muted" }, "鳥取県の市町村地図を読み込み中..."),
  ]);

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
    el("section", { class: "prefecture-map-panel" }, [
      el("h2", { class: "section-title" }, "地図から選ぶ"),
      el("div", { class: "prefecture-map-layout" }, [
        prefectureCouncil
          ? el("div", { class: "prefecture-assembly-wrap" }, [
              el("p", { class: "map-caption" }, "県議会"),
              renderCouncilCard(prefectureCouncil, prefecture),
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
  );

  const comparison = renderPrefectureComparison(summaries, prefecture);
  if (comparison) root.appendChild(comparison);

  root.appendChild(
    el(
      "div",
      { class: "council-grid" },
      councils.map((council) => renderCouncilCard(council, prefecture)),
    ),
  );

  hydrateMunicipalityMap(mapFrame, prefecture);
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
