import { sourceLink } from "./data-quality.js";
import { memberPath } from "./router.js";
import { el } from "./utils.js";

const ENABLED_COUNCILS = new Set(["kurayoshi-city"]);

export function votesEnabledForCouncil(council) {
  return ENABLED_COUNCILS.has(council?.id);
}

export function renderMemberVoteSection(votes, member, council, route) {
  if (!votesEnabledForCouncil(council)) {
    return null;
  }

  const memberVotes = (votes || [])
    .map((vote) => {
      const item = (vote.votes_by_member || [])
        .find((entry) => entry.member_id === member.id);
      return item ? { vote, item } : null;
    })
    .filter(Boolean)
    .sort((a, b) => (b.vote.date || "").localeCompare(a.vote.date || ""));

  const section = el("section", { class: "vote-section" });
  const listRoot = el("div", { class: "vote-list-root" });
  const filterId = `split-votes-${member.id}`;
  const checkbox = el("input", { id: filterId, type: "checkbox" });

  function renderList() {
    const visibleVotes = checkbox.checked
      ? memberVotes.filter(({ vote }) => isDividedVote(vote))
      : memberVotes;
    listRoot.innerHTML = "";
    listRoot.appendChild(
      visibleVotes.length
        ? el("ul", { class: "vote-list" }, visibleVotes.map(renderMemberVoteItem))
        : el("p", { class: "empty-message" }, "この条件に当てはまる賛否の記録はありません。"),
    );
  }

  checkbox.addEventListener("change", renderList);
  section.append(
    el("h2", { class: "section-title" }, `賛否の記録（${memberVotes.length}件）`),
    el("p", { class: "muted" }, "議員別賛否PDFから取得した記録です。件数は取得範囲や議長職などにより変わります。"),
    el("label", { class: "vote-filter", for: filterId }, [
      checkbox,
      el("span", {}, "賛否が分かれた議決だけ表示"),
    ]),
    listRoot,
  );
  renderList();
  return section;
}

export function renderCouncilVoteSection(votes, votesMeta, council, members, route) {
  if (!votesEnabledForCouncil(council)) {
    return el("section", { class: "vote-section" }, [
      el("h2", { class: "section-title" }, "議決一覧"),
      el("p", { class: "empty-message" }, "この議会の賛否表示は次の確認段階で展開します。"),
    ]);
  }
  if (!votesMeta) {
    return el("section", { class: "vote-section" }, [
      el("h2", { class: "section-title" }, "議決一覧"),
      el("p", { class: "empty-message" }, "議員別賛否データはまだ取得していません。"),
    ]);
  }

  const memberMap = new Map((members || []).map((member) => [member.id, member]));
  const sortedVotes = [...(votes || [])].sort((a, b) => {
    const dateCompare = (b.date || "").localeCompare(a.date || "");
    if (dateCompare) return dateCompare;
    return (a.bill_title || "").localeCompare(b.bill_title || "", "ja");
  });

  return el("section", { class: "vote-section" }, [
    el("h2", { class: "section-title" }, `議決一覧（${sortedVotes.length}件）`),
    el("p", { class: "muted" }, "議案ごとの賛成・反対の人数を表示します。展開すると各議員の票を確認できます。"),
    el("div", { class: "vote-detail-list" },
      sortedVotes.map((vote) => renderCouncilVoteDetail(vote, council, route, memberMap)),
    ),
  ]);
}

function renderMemberVoteItem({ vote, item }) {
  return el("li", { class: "vote-item" }, [
    el("div", { class: "vote-date" }, vote.date || "日付なし"),
    el("div", { class: "vote-main" }, [
      el("div", { class: "vote-title" }, vote.bill_title || "議案名なし"),
      el("div", { class: "vote-meta-line" }, [
        renderVoteBadge(item.vote),
        el("span", {}, `議決結果: ${vote.result || "データなし"}`),
        isDividedVote(vote)
          ? el("span", { class: "vote-chip" }, "賛否が分かれた議決")
          : null,
      ]),
      sourceLink(vote.source_url, "賛否の出典"),
    ]),
  ]);
}

function renderCouncilVoteDetail(vote, council, route, memberMap) {
  const counts = voteCounts(vote);
  const details = el("details", { class: "vote-detail" }, [
    el("summary", { class: "vote-summary" }, [
      el("span", { class: "vote-summary-date" }, vote.date || "日付なし"),
      el("span", { class: "vote-summary-title" }, vote.bill_title || "議案名なし"),
      el("span", { class: "vote-summary-counts" }, [
        `賛成 ${counts["賛成"] || 0} / 反対 ${counts["反対"] || 0}`,
      ]),
      el("span", { class: "vote-summary-result" }, vote.result || "結果なし"),
    ]),
    el("div", { class: "vote-detail-body" }, [
      el("p", { class: "vote-source" }, sourceLink(vote.source_url, "公式PDFで確認")),
      el("div", { class: "vote-member-grid" },
        (vote.votes_by_member || []).map((entry) =>
          renderVoteMemberCell(entry, council, route, memberMap),
        ),
      ),
    ]),
  ]);
  return details;
}

function renderVoteMemberCell(entry, council, route, memberMap) {
  const member = entry.member_id ? memberMap.get(entry.member_id) : null;
  const label = member?.name || entry.member_name || "名前不明";
  const nameNode = member
    ? el("a", {
        href: memberPath(
          council.prefecture || route.prefecture || "tottori",
          council.id,
          member.id,
        ),
      }, label)
    : el("span", {}, label);
  return el("div", { class: "vote-member-cell" }, [
    el("span", { class: "vote-member-name" }, nameNode),
    renderVoteBadge(entry.vote),
    entry.member_id ? null : el("span", { class: "vote-former-note" }, "現在の議員名簿にいません"),
  ]);
}

function renderVoteBadge(value) {
  return el("span", {
    class: `vote-badge ${voteClass(value)}`,
    title: voteHelpText(value),
  }, voteDisplayText(value));
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

function voteDisplayText(value) {
  if (value === "議長") return "議長（採決に加わらず）";
  if (value === "除斥") return "除斥";
  return value || "不明";
}

function voteHelpText(value) {
  if (value === "議長") return "議長は慣例により採決に加わりません。";
  if (value === "除斥") return "利害関係があるため採決から外れた状態です。";
  return value || "";
}

function voteClass(value) {
  if (value === "賛成") return "is-yes";
  if (value === "反対") return "is-no";
  if (value === "議長") return "is-chair";
  if (value === "除斥") return "is-recusal";
  if (value === "継続審査") return "is-continued";
  return "is-other";
}
