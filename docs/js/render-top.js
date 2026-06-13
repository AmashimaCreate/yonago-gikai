import { prefPath } from "./router.js?v=20260614-finance-merged";
import { el } from "./utils.js?v=20260614-finance-merged";

export function renderTop(root) {
  root.innerHTML = "";
  const mapFrame = el("div", { class: "map-frame japan-map-frame" }, [
    el("p", { class: "muted" }, "日本地図を読み込み中..."),
  ]);

  root.appendChild(
    el("section", { class: "national-hero page-card" }, [
      el("div", { class: "national-copy" }, [
        el("p", { class: "eyebrow" }, "全国トップ"),
        el("h2", { class: "section-title" }, "対応地域から議会を見る"),
        el(
          "p",
          {},
          "現在は鳥取県のみ対応しています。地図または地域カードから進めます。",
        ),
      ]),
      el("div", { class: "national-map-wrap" }, [
        mapFrame,
        el("section", { class: "supported-region-list", "aria-labelledby": "supported-regions-title" }, [
          el("h3", { id: "supported-regions-title" }, "対応地域"),
          el("div", { class: "supported-region-grid" }, [
            renderSupportedRegionCard({
              name: "鳥取県",
              href: prefPath("tottori"),
              summary: "県と4市、計5議会の基本情報・議決・発言を掲載",
              status: "対応中",
            }),
          ]),
        ]),
      ]),
    ]),
  );

  hydrateJapanMap(mapFrame);
}

function renderSupportedRegionCard(region) {
  return el("a", { class: "supported-region-card", href: region.href }, [
    el("span", { class: "region-card-status" }, region.status),
    el("strong", {}, region.name),
    el("span", {}, region.summary),
    el("small", {}, "地域ページへ"),
  ]);
}

async function hydrateJapanMap(container) {
  try {
    const response = await fetch("assets/maps/japan-prefectures.svg");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    container.innerHTML = await response.text();

    const svg = container.querySelector("svg");
    if (!svg) throw new Error("SVG root not found");
    svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", "日本地図。現在は鳥取県のみ選択できます。");
    svg.removeAttribute("width");
    svg.removeAttribute("height");

    container.querySelectorAll("[data-code]").forEach((region) => {
      region.classList.add("map-region", "is-disabled");
      region.setAttribute("aria-disabled", "true");
    });

    const tottori = container.querySelector('[data-code="31"]');
    if (!tottori) throw new Error("Tottori region not found");
    tottori.classList.remove("is-disabled");
    tottori.classList.add("is-active");
    tottori.setAttribute("role", "link");
    tottori.setAttribute("tabindex", "0");
    tottori.setAttribute("aria-label", "鳥取県ページへ");
    tottori.removeAttribute("aria-disabled");
    tottori.addEventListener("click", () => {
      window.location.href = prefPath("tottori");
    });
    tottori.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      window.location.href = prefPath("tottori");
    });
  } catch (error) {
    console.warn("Failed to load Japan map", error);
    container.innerHTML = "";
    container.appendChild(
      el(
        "p",
        { class: "caution-note" },
        "地図を読み込めませんでした。対応地域一覧から選択してください。",
      ),
    );
  }
}
