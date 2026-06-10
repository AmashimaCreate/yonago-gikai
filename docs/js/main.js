import { state } from "./state.js";
import { el } from "./utils.js";
import { filteredMembers } from "./search.js";
import { renderProfile } from "./render-profile.js";
import {
  renderKaihaView,
  renderCommitteeView,
  renderRoleView,
  renderTermView,
} from "./render-members.js";

function renderMeta() {
  const node = document.getElementById("meta");
  if (!node) return;
  const meta = state.membersMeta;
  const members = state.members;
  if (!meta) {
    node.textContent = `現在 ${members.length} 人を表示`;
    return;
  }
  const fetched = meta.updated_at
    ? new Date(meta.updated_at).toLocaleString("ja-JP")
    : "?";
  node.textContent = `現在 ${members.length} 人 / 最終取得 ${fetched}`;
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
  input.placeholder = "氏名 / ふりがな / 会派 / 委員会 で検索";
}

function render() {
  const main = document.getElementById("main");
  renderProfile(
    document.getElementById("profile"),
    state.profile,
    state.members.length,
    state.membersMeta,
  );
  updateSearchPlaceholder();
  renderMeta();

  const filtered = filteredMembers();
  updateMatchCount(filtered.length);

  if (state.query.trim() && filtered.length === 0) {
    main.innerHTML = "";
    main.appendChild(
      el("p", { class: "empty-message" }, "該当する議員はいません。"),
    );
    return;
  }

  if (state.view === "kaiha") renderKaihaView(main, filtered);
  else if (state.view === "committee") renderCommitteeView(main, filtered);
  else if (state.view === "role") renderRoleView(main, filtered);
  else if (state.view === "term") renderTermView(main, filtered);
}

function setupTabs() {
  const tabs = document.querySelectorAll(".view-tab");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const view = tab.dataset.view;
      if (!view || view === state.view) return;
      tabs.forEach((t) => t.classList.toggle("is-active", t === tab));
      state.view = view;
      render();
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
    render();
  });

  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      input.value = "";
      state.query = "";
      clearBtn.hidden = true;
      input.focus();
      render();
    });
  }
}

async function load() {
  const status = document.getElementById("status");
  try {
    const membersRes = await fetch(
      "./data/yonago-city/members.json",
      { cache: "no-cache" },
    );
    if (!membersRes.ok) throw new Error(`members.json: ${membersRes.status}`);
    const data = await membersRes.json();
    state.members = Array.isArray(data.members) ? data.members : [];
    state.membersMeta = data;

    const profileRes = await fetch(
      "./data/yonago-city/profile.json",
      { cache: "no-cache" },
    );
    if (profileRes.ok) {
      state.profile = await profileRes.json();
    } else {
      console.warn(`profile.json: ${profileRes.status}`);
    }

    render();
  } catch (err) {
    console.error(err);
    if (status) status.textContent = `読み込みに失敗しました: ${err.message}`;
  }
}

// 起動: type="module" は defer 同等で DOM 構築後に実行されるため、
// DOMContentLoaded を待たずに直接呼び出して問題なし。
setupTabs();
setupSearch();
load();
