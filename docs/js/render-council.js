import { dataQualityPanel } from "./data-quality.js";
import { renderFactionCompositionChart } from "./render-faction-chart.js";
import { formatDecimal, formatPeople, formatYen } from "./render-profile.js";
import { renderProfileVisualization } from "./render-profile-viz.js";
import { renderCouncilVoteSection } from "./render-votes.js";
import {
  renderCommitteeView,
  renderKaihaView,
  kaihaColor,
  memberFaction,
  renderRoleView,
  renderTermView,
} from "./render-members.js";
import { memberPath } from "./router.js";
import { el } from "./utils.js";

export function renderCouncilPage(root, state, filteredMembers) {
  root.innerHTML = "";
  if (isStageOneCouncil(state)) {
    renderStageOneCouncilPage(root, state, filteredMembers);
    return;
  }

  root.appendChild(dataQualityPanel({
    membersMeta: state.membersMeta,
    speechesMeta: state.speechesMeta,
    votesMeta: state.votesMeta,
    council: state.currentCouncil,
  }));

  if (state.view === "votes") {
    root.appendChild(renderCouncilVoteSection(
      state.votes,
      state.votesMeta,
      state.currentCouncil,
      state.members,
      state.route,
    ));
    return;
  }

  const factionChart = renderFactionCompositionChart(state.members, state.membersMeta);
  if (factionChart) root.appendChild(factionChart);

  const profileViz = renderProfileVisualization(state.profile, state.councilSummaries);
  if (profileViz) root.appendChild(profileViz);

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

function isStageOneCouncil(state) {
  return state.currentCouncil?.prefecture === "tottori";
}

function renderStageOneCouncilPage(root, state, filteredMembers) {
  root.appendChild(renderCouncilHero(state));
  root.appendChild(renderRecentVoteHighlights(state));
  root.appendChild(renderFaceLineupSection(filteredMembers, state));

  const pastRecords = renderPastRecordsDetails(state);
  if (pastRecords) root.appendChild(pastRecords);

  root.appendChild(renderStageTabPanel(state));
  if (state.view !== "kaiha") {
    root.appendChild(renderStageTabContent(state, filteredMembers));
  }
}

function renderCouncilHero(state) {
  const profile = state.profile || {};
  const population = profile.population;
  const budget = profile.budget_general_yen;
  const fiscalIndex = profile.fiscal_index;
  const perCapita = profile.per_capita || {};
  const areaName = areaNameForCouncil(state.currentCouncil);
  const areaType = areaTypeLabel(state.currentCouncil);

  return el("section", { class: "council-hero page-card" }, [
    el("div", { class: "hero-copy" }, [
      el("p", { class: "eyebrow" }, state.currentCouncil.type === "prefecture" ? "この県の今" : "この街の今"),
      el("h2", {}, `${areaName}の今`),
      el("p", {}, `${areaName}の規模と議会の形を見ます。`),
    ]),
    el("div", { class: "hero-metrics" }, [
      heroMetric("人口", formatPeople(population?.value), `${areaType}の規模`),
      heroMetric("一般会計予算", formatYen(budget?.value), "年間のお金の大きさ"),
      heroMetric("議員数", formatPeople(state.members.length), "現在の名簿"),
    ]),
    el("details", { class: "profile-details" }, [
      el("summary", {}, "基礎データをもう少し見る"),
      el("dl", { class: "profile-detail-list" }, [
        detailPair("世帯数", formatPeople(profile.households?.value)?.replace("人", "世帯")),
        detailPair("財政力指数", formatDecimal(fiscalIndex?.value), "1.0以上なら国からの仕送りなしでやっていける目安"),
        detailPair("議員1人あたり住民数", formatPeople(perCapita.population_per_member)),
        detailPair(`${areaType}債残高(1人あたり)`, formatYen(perCapita.debt_per_capita_yen)),
      ].filter(Boolean).flat()),
      sourceLine("基礎データ", [
        profileSource(population, "人口"),
        profileSource(budget, "予算"),
        state.membersMeta?.source_url
          ? { label: "議員名簿", url: state.membersMeta.source_url }
          : null,
      ]),
    ]),
  ]);
}

function heroMetric(label, value, note) {
  if (!value) return null;
  return el("article", { class: "hero-metric" }, [
    el("span", { class: "hero-metric-label" }, label),
    el("strong", { class: "hero-metric-value" }, value),
    el("span", { class: "hero-metric-note" }, note),
  ]);
}

function detailPair(label, value, note = null) {
  if (!value) return null;
  return [
    el("dt", {}, label),
    el("dd", {}, [
      el("span", {}, value),
      note ? el("small", {}, note) : null,
    ]),
  ];
}

function profileSource(item, fallbackLabel) {
  if (!item?.source_url) return null;
  return {
    label: item.source_name || fallbackLabel,
    url: item.source_url,
  };
}

function renderFaceLineupSection(members, state) {
  const isFiltered = state.query.trim().length > 0;
  const groups = groupMembersByFaction(members);
  const body = isFiltered && members.length === 0
    ? [el("p", { class: "empty-message" }, "該当する議員はいません。")]
    : [
        renderCompactFactionChart(state.members),
        el("div", { class: "face-lineup-groups" }, groups.map(([faction, list]) =>
          renderFactionFaceGroup(faction, list, state),
        )),
      ];
  return el("section", { class: "face-lineup-section" }, [
    el("div", { class: "section-heading-row" }, [
      el("div", {}, [
        el("p", { class: "eyebrow" }, "決めている人たち"),
        el("h2", { class: "section-title" }, isFiltered ? "検索結果" : "写真で見る現在の議員"),
      ]),
      el("p", { class: "section-count" }, `${members.length}人`),
    ]),
    ...body,
    sourceLine("議員名簿", [
      state.membersMeta?.source_url
        ? { label: state.membersMeta.source_name || "公式名簿", url: state.membersMeta.source_url }
        : null,
    ]),
  ]);
}

function renderCompactFactionChart(members) {
  const groups = groupMembersByFaction(members);
  const total = groups.reduce((sum, [, list]) => sum + list.length, 0);
  if (!total) return null;

  return el("div", { class: "compact-faction-chart" }, [
    el("div", { class: "compact-faction-head" }, [
      el("h3", {}, "会派構成"),
      el("p", {}, `合計${total}人。色は識別用です。`),
    ]),
    el("div", { class: "compact-faction-bar", role: "img", "aria-label": `会派別人数。合計${total}人。` },
      groups.map(([faction, list]) =>
        el("button", {
          type: "button",
          class: "compact-faction-segment",
          style: `--kaiha-color: ${kaihaColor(faction)}; --segment-width: ${(list.length / total) * 100}%;`,
          "aria-label": `${faction} ${list.length}人。顔ぶれへ移動`,
          onclick: () => requestFactionFocus(faction),
        }, `${list.length}人`),
      ),
    ),
    el("div", { class: "compact-faction-legend" }, groups.map(([faction, list]) =>
      el("button", {
        type: "button",
        style: `--kaiha-color: ${kaihaColor(faction)}; --faction-color: ${kaihaColor(faction)};`,
        onclick: () => requestFactionFocus(faction),
      }, [
        el("span", { class: "faction-chart-swatch", "aria-hidden": "true" }),
        el("span", {}, faction),
        el("strong", {}, `${list.length}人`),
      ]),
    )),
  ]);
}

function requestFactionFocus(faction) {
  window.dispatchEvent(
    new CustomEvent("council:faction-focus", { detail: { faction } }),
  );
}

function groupMembersByFaction(members) {
  const map = new Map();
  for (const member of members || []) {
    const faction = memberFaction(member);
    if (!map.has(faction)) map.set(faction, []);
    map.get(faction).push(member);
  }
  return [...map.entries()];
}

function renderFactionFaceGroup(faction, members, state) {
  return el("section", {
    class: "kaiha-group ux-kaiha-face-group",
    "data-faction": faction,
    tabindex: "-1",
    style: `--kaiha-color: ${kaihaColor(faction)};`,
  }, [
    el("div", { class: "kaiha-header compact" }, [
      el("h3", { class: "kaiha-name" }, faction),
      el("span", { class: "kaiha-count" }, `${members.length}人`),
    ]),
    el("div", { class: "face-grid" }, members.map((member) =>
      renderFaceCard(member, state),
    )),
  ]);
}

function renderFaceCard(member, state) {
  const faction = memberFaction(member);
  const term = typeof member.elected_count === "number"
    ? `当選 ${member.elected_count} 回`
    : "当選回数: データなし";
  const photo = member.photo_url
    ? el("img", {
        class: "face-photo",
        src: member.photo_url,
        alt: `${member.name}議員の写真`,
        loading: "lazy",
        referrerpolicy: "no-referrer",
      })
    : el("div", { class: "face-photo face-photo-placeholder" }, "写真なし");
  if (photo.tagName === "IMG") {
    photo.addEventListener("error", () => {
      photo.replaceWith(el("div", { class: "face-photo face-photo-placeholder" }, "写真なし"));
    });
  }
  return el("a", {
    class: "face-card",
    href: memberPath(
      state.currentCouncil.prefecture || state.route.prefecture || "tottori",
      state.currentCouncil.id,
      member.id,
    ),
    style: `--kaiha-color: ${kaihaColor(faction)};`,
  }, [
    photo,
    el("strong", { class: "face-name" }, member.name),
    el("span", { class: "face-faction" }, faction),
    el("span", { class: "face-term" }, term),
  ]);
}

function renderRecentVoteHighlights(state) {
  const votes = [...(state.votes || [])].sort((a, b) => {
    const dateCompare = (b.date || "").localeCompare(a.date || "");
    if (dateCompare) return dateCompare;
    return (a.bill_title || "").localeCompare(b.bill_title || "", "ja");
  });
  if (!votes.length) {
    return el("section", { class: "recent-votes page-card" }, [
      el("div", { class: "section-heading-row" }, [
        el("div", {}, [
          el("p", { class: "eyebrow" }, "最近決まったこと"),
          el("h2", { class: "section-title" }, "議決データは未収録です"),
        ]),
      ]),
      el("p", { class: "empty-message" }, voteMissingMessage(state.currentCouncil)),
    ]);
  }

  const latestDate = votes[0].date;
  const latestVotes = votes.filter((vote) => vote.date === latestDate);
  const divided = latestVotes.filter(isDividedVote);
  const highlighted = (divided.length ? divided : latestVotes).slice(0, 3);

  const tabButton = el("button", { type: "button", class: "text-button" }, "議決一覧へ");
  tabButton.addEventListener("click", () => {
    window.dispatchEvent(
      new CustomEvent("council:view-change", { detail: { view: "votes" } }),
    );
  });

  return el("section", { class: "recent-votes page-card" }, [
    el("div", { class: "section-heading-row" }, [
      el("div", {}, [
        el("p", { class: "eyebrow" }, "最近決まったこと"),
        el("h2", { class: "section-title" }, "直近の議決ハイライト"),
      ]),
      el("span", { class: "stage-link-wrap" }, [tabButton]),
    ]),
    el("p", { class: "muted" }, divided.length
      ? "賛否が分かれた議決を優先表示しています。"
      : "直近の議決を表示しています。"),
    el("div", { class: "vote-highlight-grid" }, highlighted.map(renderVoteHighlightCard)),
    sourceLine("議決", [
      highlighted.find((vote) => vote.source_url)
        ? { label: "議員別賛否PDF", url: highlighted.find((vote) => vote.source_url).source_url }
        : null,
    ]),
  ]);
}

function renderStageTabPanel(state) {
  const tabs = [
    ["kaiha", "会派"],
    ["committee", "委員会"],
    ["role", "役職"],
    ["term", "当選回数"],
    ["votes", "議決一覧"],
  ];
  const searchId = "stage-council-search";
  const clearButton = el("button", {
    type: "button",
    class: "search-clear",
    hidden: state.query.length === 0 ? "" : null,
    "aria-label": "検索をクリア",
    onclick: () => {
      window.dispatchEvent(
        new CustomEvent("council:query-change", { detail: { query: "" } }),
      );
    },
  }, "×");

  return el("section", { class: "stage-tab-panel page-card" }, [
    el("div", { class: "section-heading-row" }, [
      el("div", {}, [
        el("p", { class: "eyebrow" }, "もっと詳しく見る"),
        el("h2", { class: "section-title" }, "議会の中身を見る"),
      ]),
    ]),
    el("div", { class: "stage-tabs", role: "tablist", "aria-label": "議会ページの表示切り替え" },
      tabs.map(([view, label]) =>
        el("button", {
          type: "button",
          class: `view-tab ${state.view === view ? "is-active" : ""}`,
          "data-view": view,
          role: "tab",
          "aria-selected": state.view === view ? "true" : "false",
          onclick: () => {
            window.dispatchEvent(
              new CustomEvent("council:view-change", { detail: { view } }),
            );
          },
        }, label),
      ),
    ),
    el("div", { class: "search-row stage-search-row", hidden: state.view === "votes" ? "" : null }, [
      el("input", {
        id: searchId,
        type: "search",
        class: "search-input",
        placeholder: `${state.currentCouncil?.name || "議員"}を検索`,
        autocomplete: "off",
        value: state.query,
        oninput: (event) => {
          window.dispatchEvent(
            new CustomEvent("council:query-change", {
              detail: { query: event.target.value },
            }),
          );
        },
      }),
      clearButton,
      el("span", { class: "match-count" }, state.query.trim()
        ? `${state.members.length}人中 ${filteredMemberCount(state)}人を表示`
        : ""),
    ]),
  ]);
}

function filteredMemberCount(state) {
  const query = state.query.trim().toLowerCase();
  if (!query) return state.members.length;
  return state.members.filter((member) => {
    const haystack = [
      member.name,
      member.name_kana,
      member.faction,
      ...(member.committees || []),
      ...(member.positions || []),
    ].filter(Boolean).join(" ").toLowerCase();
    return haystack.includes(query);
  }).length;
}

function renderStageTabContent(state, filteredMembers) {
  const section = el("section", { class: "stage-tab-content" });
  if (state.view === "votes") {
    section.appendChild(renderCouncilVoteSection(
      state.votes,
      state.votesMeta,
      state.currentCouncil,
      state.members,
      state.route,
    ));
    return section;
  }

  const listRoot = el("div", { class: "member-list-root redesigned-tab-panel" });
  section.appendChild(listRoot);
  if (state.query.trim() && filteredMembers.length === 0) {
    listRoot.appendChild(
      el("p", { class: "empty-message" }, "該当する議員はいません。"),
    );
    return section;
  }
  if (state.view === "committee") renderCommitteeView(listRoot, filteredMembers);
  else if (state.view === "role") renderRoleView(listRoot, filteredMembers);
  else if (state.view === "term") renderTermView(listRoot, filteredMembers);
  return section;
}

function renderVoteHighlightCard(vote) {
  const counts = voteCounts(vote);
  return el("article", { class: "vote-highlight-card" }, [
    el("span", { class: "vote-date" }, vote.date || "日付なし"),
    el("h3", {}, vote.bill_title || "議案名なし"),
    el("div", { class: "vote-highlight-counts" }, [
      el("span", { class: "vote-badge is-yes" }, `○ 賛成 ${counts["賛成"] || 0}`),
      el("span", { class: "vote-badge is-no" }, `× 反対 ${counts["反対"] || 0}`),
    ]),
    el("p", { class: "vote-result" }, `結果: ${vote.result || "結果なし"}`),
  ]);
}

function renderPastRecordsDetails(state) {
  const formerSpeeches = groupFormerSpeeches(state.speeches)
    .map(([label, items]) => ({ label, count: items.length, type: "発言" }));
  const formerVotes = groupFormerVotes(state.votes)
    .map(([label, count]) => ({ label, count, type: "議決" }));
  const records = [...formerSpeeches, ...formerVotes]
    .sort((a, b) => a.label.localeCompare(b.label, "ja"));
  const total = records.reduce((sum, record) => sum + record.count, 0);
  if (!total) return null;

  return el("details", { class: "past-records page-card" }, [
    el("summary", {}, `過去の議員の記録 ${total}件`),
    el("p", { class: "muted" }, "現在の議員名簿と照合できない発言・票です。過去議員や表記揺れの可能性があるため、現職議員ページには混ぜていません。"),
    el("ul", { class: "past-record-list" }, records.map((record) =>
      el("li", {}, `${record.label}: ${record.type} ${record.count}件`),
    )),
  ]);
}

function groupFormerVotes(votes) {
  const map = new Map();
  for (const vote of votes || []) {
    for (const entry of vote.votes_by_member || []) {
      if (entry.member_id) continue;
      const label = entry.member_name || "投票者名不明";
      map.set(label, (map.get(label) || 0) + 1);
    }
  }
  return [...map.entries()];
}

function sourceLine(label, sources) {
  const unique = [];
  const seen = new Set();
  for (const source of sources.filter(Boolean)) {
    const key = source.url || source.label;
    if (seen.has(key)) continue;
    seen.add(key);
    unique.push(source);
  }
  if (!unique.length) return null;
  const children = [`出典: ${label}（`];
  unique.forEach((source, index) => {
    if (index) children.push(" / ");
    children.push(
      source.url
        ? el("a", { href: source.url, target: "_blank", rel: "noopener" }, source.label)
        : source.label,
    );
  });
  children.push("）");
  return el("p", { class: "section-source" }, children);
}

function voteCounts(vote) {
  const counts = {};
  for (const entry of vote.votes_by_member || []) {
    const value = entry.vote || "不明";
    counts[value] = (counts[value] || 0) + 1;
  }
  return counts;
}

function isDividedVote(vote) {
  const counts = voteCounts(vote);
  return (counts["賛成"] || 0) > 0 && (counts["反対"] || 0) > 0;
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

function areaNameForCouncil(council) {
  if (!council?.name) return "この地域";
  return council.name
    .replace(/議会$/, "")
    .replace(/市$/, "市")
    .replace(/県$/, "県");
}

function areaTypeLabel(council) {
  if (council?.type === "prefecture") return "県";
  const name = council?.name || "";
  if (name.includes("町議会")) return "町";
  if (name.includes("村議会")) return "村";
  return "市";
}

function voteMissingMessage(council) {
  if (council?.id === "tottori-city") {
    return "賛否PDFが機械可読でない形式のため未収録です（対応検討中）。";
  }
  if (council?.id === "yonago-city") {
    return "議員別の賛否は公式に公開されていません（議決結果のみ）。";
  }
  return "議員別賛否データはまだ取得していません。";
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
