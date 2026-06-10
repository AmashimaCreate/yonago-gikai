import { dataQualityPanel } from "./data-quality.js";
import {
  renderCommitteeView,
  renderKaihaView,
  renderRoleView,
  renderTermView,
} from "./render-members.js";
import { el } from "./utils.js";

export function renderCouncilPage(root, state, filteredMembers) {
  root.innerHTML = "";
  root.appendChild(dataQualityPanel({
    membersMeta: state.membersMeta,
    speechesMeta: state.speechesMeta,
    council: state.currentCouncil,
  }));

  const former = groupFormerSpeeches(state.speeches);
  if (former.length) {
    root.appendChild(renderFormerSpeeches(former));
  }

  const listRoot = el("div", { class: "member-list-root" });
  root.appendChild(listRoot);

  if (state.query.trim() && filteredMembers.length === 0) {
    listRoot.appendChild(
      el("p", { class: "empty-message" }, "該当する議員はいません。"),
    );
    return;
  }

  if (state.view === "kaiha") renderKaihaView(listRoot, filteredMembers);
  else if (state.view === "committee") renderCommitteeView(listRoot, filteredMembers);
  else if (state.view === "role") renderRoleView(listRoot, filteredMembers);
  else if (state.view === "term") renderTermView(listRoot, filteredMembers);
}

function groupFormerSpeeches(speeches) {
  const map = new Map();
  for (const speech of speeches || []) {
    if (speech.member_id) continue;
    const label = speech.speaker_label || "発言者名不明";
    if (!map.has(label)) map.set(label, []);
    map.get(label).push(speech);
  }
  return [...map.entries()].sort((a, b) => a[0].localeCompare(b[0], "ja"));
}

function renderFormerSpeeches(groups) {
  return el("section", { class: "former-speeches" }, [
    el("h2", { class: "section-title" }, "現名簿外の発言"),
    el("p", { class: "muted" }, "現在の議員名簿と照合できない発言です。過去議員や表記揺れの可能性があるため、現職議員ページには混ぜていません。"),
    el(
      "ul",
      { class: "former-list" },
      groups.map(([label, items]) =>
        el("li", {}, `${label}: ${items.length}件`),
      ),
    ),
  ]);
}
