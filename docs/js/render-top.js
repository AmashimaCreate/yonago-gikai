import { prefPath } from "./router.js";
import { el } from "./utils.js";

export function renderTop(root) {
  root.innerHTML = "";
  root.appendChild(
    el("section", { class: "intro-panel" }, [
      el("h2", { class: "section-title" }, "全国トップ"),
      el(
        "p",
        {},
        "全国の都道府県から、対応済みの議会ページへ進む入口です。",
      ),
      el(
        "p",
        { class: "muted" },
        "現在は鳥取県のみ対応しています。日本地図ナビゲーションは次の実装ステップで追加します。",
      ),
      el("p", {}, [
        el("a", { class: "button-link", href: prefPath("tottori") }, "鳥取県ページを見る"),
      ]),
    ]),
  );
}
