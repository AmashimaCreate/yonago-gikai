import { el } from "./utils.js";

export function renderAbout(root) {
  root.innerHTML = "";
  root.append(
    el("section", { class: "about-page page-card" }, [
      el("h2", { class: "section-title" }, "このサイトについて"),
      el("div", { class: "about-lead" }, [
        el("p", {}, "議会の公開情報を、市民が見つけやすい形に並べ直す非公式サイトです。"),
        el("p", {}, "議員名簿、基礎データ、発言インデックス、議決への賛否を、自治体をまたいで同じ形で見られるようにします。"),
        el("p", {}, "正確な情報は、各議会・自治体の公式発表を優先してください。"),
      ]),
    ]),
    el("section", { class: "about-page page-card" }, [
      el("h2", { class: "section-title" }, "データの出典・取得方法・更新頻度"),
      el("ul", { class: "about-list" }, [
        el("li", {}, "議員名簿: 各議会の公式名簿を自動取得または手作業で転記しています。"),
        el("li", {}, "基礎データ: 自治体公式資料、決算カード等の一次ソースから入力し、派生値を自動計算しています。"),
        el("li", {}, "発言インデックス: 会議録検索システムから、本会議の議員発言者を対象に取得しています。"),
        el("li", {}, "議員別賛否: 公式PDFから機械抽出できる範囲で取得しています。"),
        el("li", {}, "更新頻度: 月1回の自動更新を基本に、手作業確認が必要なデータは随時更新します。"),
      ]),
    ]),
    el("section", { class: "about-page page-card" }, [
      el("h2", { class: "section-title" }, "地図クレジット"),
      el("ul", { class: "about-list" }, [
        el("li", {}, [
          "日本地図: ",
          el("a", {
            href: "https://github.com/geolonia/japanese-prefectures",
            target: "_blank",
            rel: "noopener",
          }, "geolonia/japanese-prefectures"),
          " (GFDL)",
        ]),
        el("li", {}, [
          "鳥取県市町村地図: ",
          el("a", {
            href: "https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N03-2024.html",
            target: "_blank",
            rel: "noopener",
          }, "国土数値情報 行政区域データ"),
          " (PDL1.0)",
        ]),
      ]),
    ]),
    el("section", { class: "about-page page-card" }, [
      el("h2", { class: "section-title" }, "問い合わせ"),
      el("p", {}, "問い合わせ先は公開前に掲載予定です。"),
      el("p", { class: "muted" }, "免責文言は公開前に最終判断します。"),
    ]),
  );
}
