import { loadCouncilBundle, loadCouncils, loadCouncilSummaries } from "./data-loader.js";
import { renderCouncilPage } from "./render-council.js";
import { renderMemberPage } from "./render-member.js";
import { renderPrefecturePage } from "./render-prefecture.js";
import { renderProfile } from "./render-profile.js";
import { renderTop } from "./render-top.js";
import { parseRoute } from "./router.js";
import { filteredMembers } from "./search.js";
import { state } from "./state.js";
import { el } from "./utils.js";

function titleNode() {
  return document.getElementById("page-title");
}

function leadNode() {
  return document.getElementById("page-lead");
}

function metaNode() {
  return document.getElementById("meta");
}

function mainNode() {
  return document.getElementById("main");
}

function setHeader({ title, lead, meta = "" }) {
  document.title = title.endsWith("議会見える化")
    ? title
    : `${title} | 議会見える化`;
  titleNode().textContent = title;
  leadNode().textContent = lead;
  metaNode().textContent = meta;
}

function showCouncilNav(show) {
  const nav = document.getElementById("view-nav");
  if (nav) nav.hidden = !show;
  const profile = document.getElementById("profile");
  if (profile && !show) {
    profile.hidden = true;
    profile.innerHTML = "";
  }
}

function renderMeta() {
  const node = metaNode();
  const meta = state.membersMeta;
  const members = state.members;
  if (!meta) {
    node.textContent = "";
    return;
  }
  const fetched = meta.updated_at
    ? new Date(meta.updated_at).toLocaleString("ja-JP")
    : "?";
  const type = councilTypeLabel(state.currentCouncil);
  node.textContent = `${type} / 現在 ${members.length}人 / 最終更新 ${fetched}`;
}

function updateMatchCount(filteredCount) {
  const node = document.getElementById("match-count");
  if (!node) return;
  const total = state.members.length;
  if (state.query.trim()) {
    node.textContent = `${total}人中 ${filteredCount}人を表示`;
  } else {
    node.textContent = "";
  }
}

function updateSearchPlaceholder() {
  const input = document.getElementById("search");
  if (!input) return;
  input.placeholder = `${state.currentCouncil?.name || "議員"}を検索`;
}

function syncSearchInput() {
  const input = document.getElementById("search");
  const clearBtn = document.getElementById("search-clear");
  if (!input) return;
  input.value = state.query;
  if (clearBtn) clearBtn.hidden = state.query.length === 0;
}

function updateActiveTab() {
  const tabs = document.querySelectorAll(".view-tab");
  tabs.forEach((tab) => {
    tab.classList.toggle("is-active", tab.dataset.view === state.view);
  });
}

function renderCouncilRoute() {
  setHeader({
    title: state.currentCouncil.name,
    lead: "議員名簿、自治体基礎データ、発言インデックスを同じ画面で確認します。",
  });
  showCouncilNav(true);
  updateActiveTab();
  updateSearchPlaceholder();
  syncSearchInput();
  renderProfile(
    document.getElementById("profile"),
    state.profile,
    state.members.length,
    state.membersMeta,
  );
  renderMeta();

  const filtered = filteredMembers();
  updateMatchCount(filtered.length);
  renderCouncilPage(mainNode(), state, filtered);
}

function renderMemberRoute(memberId) {
  const member = state.members.find((item) => item.id === memberId);
  setHeader({
    title: member ? member.name : "議員ページ",
    lead: state.currentCouncil.name,
  });
  showCouncilNav(false);
  renderMeta();
  renderMemberPage(mainNode(), state, memberId);
}

function renderNotFound() {
  setHeader({
    title: "ページが見つかりません",
    lead: "URLを確認してください。",
  });
  showCouncilNav(false);
  mainNode().innerHTML = "";
  mainNode().appendChild(
    el("p", { class: "empty-message" }, [
      "ページが見つかりません。 ",
      el("a", { href: "#/" }, "トップへ戻る"),
    ]),
  );
}

async function applyRoute() {
  const route = parseRoute();
  state.route = route;

  if (route.name === "redirect") {
    window.location.replace(route.to);
    return;
  }

  state.councils = await loadCouncils();

  if (route.name === "national") {
    state.currentCouncil = null;
    state.members = [];
    state.membersMeta = null;
    state.profile = null;
    state.councilSummaries = [];
    state.speeches = [];
    state.speechesMeta = null;
    state.query = "";
    setHeader({
      title: "全国 議会見える化",
      lead: "対応地域を地図と一覧から選び、議会ごとの公開データを確認できます。",
    });
    showCouncilNav(false);
    renderTop(mainNode());
    return;
  }

  if (route.name === "prefecture") {
    state.currentCouncil = null;
    state.members = [];
    state.membersMeta = null;
    state.profile = null;
    state.councilSummaries = [];
    state.speeches = [];
    state.speechesMeta = null;
    state.query = "";
    if (route.prefecture !== "tottori") {
      renderNotFound();
      return;
    }
    setHeader({
      title: "鳥取県 議会見える化",
      lead: "鳥取県内5議会の公開データを同じ形で確認できます。",
    });
    showCouncilNav(false);
    state.councilSummaries = await loadCouncilSummaries(
      state.councils.filter((council) => council.prefecture === route.prefecture),
    );
    renderPrefecturePage(
      mainNode(),
      state.councils,
      route.prefecture,
      state.councilSummaries,
    );
    return;
  }

  if (route.name === "council" || route.name === "member") {
    if (route.prefecture !== "tottori") {
      renderNotFound();
      return;
    }
    const bundle = await loadCouncilBundle(route.councilId, {
      includeSpeeches: true,
    });
    state.currentCouncil = bundle.council;
    state.members = bundle.members;
    state.membersMeta = bundle.membersMeta;
    state.profile = bundle.profile;
    state.councilSummaries = await loadCouncilSummaries(
      state.councils.filter((council) => council.prefecture === route.prefecture),
    );
    state.speeches = bundle.speeches;
    state.speechesMeta = bundle.speechesMeta;

    if (route.name === "member") {
      renderMemberRoute(route.memberId);
    } else {
      renderCouncilRoute();
    }
    return;
  }

  renderNotFound();
}

function renderWithErrorBoundary() {
  applyRoute().catch((err) => {
    console.error(err);
    showCouncilNav(false);
    setHeader({
      title: "読み込みエラー",
      lead: "データの読み込みに失敗しました。",
    });
    mainNode().innerHTML = "";
    mainNode().appendChild(
      el("p", { class: "empty-message" }, `読み込みに失敗しました: ${err.message}`),
    );
  });
}

function setupTabs() {
  const tabs = document.querySelectorAll(".view-tab");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const view = tab.dataset.view;
      if (!view || view === state.view) return;
      state.view = view;
      renderCouncilRoute();
    });
  });
}

function setupSearch() {
  const input = document.getElementById("search");
  const clearBtn = document.getElementById("search-clear");
  if (!input) return;

  input.addEventListener("input", () => {
    state.query = input.value;
    if (clearBtn) clearBtn.hidden = state.query.length === 0;
    renderCouncilRoute();
  });

  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      input.value = "";
      state.query = "";
      clearBtn.hidden = true;
      input.focus();
      renderCouncilRoute();
    });
  }
}

function setupCouncilVizEvents() {
  window.addEventListener("council:faction-focus", (event) => {
    const faction = event.detail?.faction;
    if (!faction || !state.currentCouncil) return;

    state.view = "kaiha";
    state.query = "";
    renderCouncilRoute();

    window.requestAnimationFrame(() => {
      const target = [...document.querySelectorAll(".kaiha-group")]
        .find((node) => node.dataset.faction === faction);
      if (!target) return;
      target.scrollIntoView({ behavior: "smooth", block: "start" });
      target.classList.add("is-highlighted");
      window.setTimeout(() => target.classList.remove("is-highlighted"), 1200);
    });
  });
}

function councilTypeLabel(council) {
  return council?.type === "prefecture" ? "県議会" : "市議会";
}

setupTabs();
setupSearch();
setupCouncilVizEvents();
window.addEventListener("hashchange", renderWithErrorBoundary);
renderWithErrorBoundary();
