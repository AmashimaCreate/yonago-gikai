import { sourceLink } from "./data-quality.js";
import { memberPath } from "./router.js";
import { el } from "./utils.js";

const ENABLED_COUNCILS = new Set([
  "kurayoshi-city",
  "tottori-pref",
  "sakaiminato-city",
]);
const VOTE_ORDER = ["賛成", "反対", "退席", "欠席", "議長", "除斥", "継続審査"];
const SPLIT_VOTE_THRESHOLD = 0.3;
// 県議会は1人あたり368件規模になるため、初期表示のカードは最新12件に絞る。
// 残りは同じ分類内の定例会折りたたみに残し、記録自体は隠さない。
const HIGHLIGHT_CARD_LIMIT = 12;

export function votesEnabledForCouncil(council) {
  return ENABLED_COUNCILS.has(council?.id);
}

export function renderMemberVoteSection(votes, member, council, route) {
  if (!votesEnabledForCouncil(council)) {
    return renderMemberVoteMissingSection(council);
  }
  if (!Array.isArray(votes) || votes.length === 0) {
    return renderMemberVoteMissingSection(council);
  }

  const memberVotes = (votes || [])
    .map((vote) => {
      const item = (vote.votes_by_member || [])
        .find((entry) => entry.member_id === member.id);
      return item ? { vote, item } : null;
    })
    .filter(Boolean)
    .sort((a, b) => (b.vote.date || "").localeCompare(a.vote.date || ""));

  const categorized = categorizeMemberVotes(memberVotes);
  const groups = groupVotesBySession(categorized.otherVotes);

  return el("section", { class: "vote-section member-vote-section" }, [
    el("div", { class: "section-heading-row" }, [
      el("div", {}, [
        el("p", { class: "eyebrow" }, "議案への賛否"),
        el("h2", { class: "section-title" }, "賛否の記録"),
      ]),
    ]),
    renderMemberVoteSummary(memberVotes),
    renderVoteHighlightBlock(
      "本人の票が多数派と異なった議決",
      categorized.minorityVotes,
      "この取得範囲では、本人の票が多数派と異なった議決はありません。",
    ),
    renderVoteHighlightBlock(
      "議会全体で賛否が大きく分かれた議決",
      categorized.broadSplitVotes,
      "少数側がおおむね3割以上だった議決はありません。",
    ),
    renderAllVoteGroups(groups, categorized.otherVotes.length),
    renderVoteSourceSummary(memberVotes),
  ]);
}

function renderMemberVoteMissingSection(council) {
  return el("section", { class: "vote-section member-vote-section" }, [
    el("div", { class: "section-heading-row" }, [
      el("div", {}, [
        el("p", { class: "eyebrow" }, "議案への賛否"),
        el("h2", { class: "section-title" }, "賛否の記録は未収録です"),
      ]),
    ]),
    el("p", { class: "empty-message is-compact" }, voteMissingMessage(council)),
  ]);
}

export function renderCouncilVoteSection(votes, votesMeta, council, members, route) {
  if (!votesEnabledForCouncil(council)) {
    return el("section", { class: "vote-section" }, [
      el("h2", { class: "section-title" }, "議決一覧"),
      el("p", { class: "empty-message" }, voteMissingMessage(council)),
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

function renderMemberVoteSummary(memberVotes) {
  const counts = memberVoteCounts(memberVotes);
  return el("div", { class: "member-vote-overview" }, [
    el("strong", {}, `${memberVotes.length}件`),
    el("span", {}, " — "),
    el("span", { class: "member-vote-counts" }, formatVoteCounts(counts)),
  ]);
}

function renderVoteHighlightBlock(title, votes, emptyText) {
  const cardVotes = votes.slice(0, HIGHLIGHT_CARD_LIMIT);
  const overflowVotes = votes.slice(HIGHLIGHT_CARD_LIMIT);

  return el("section", { class: "divided-vote-block" }, [
    el("h3", {}, `${title}（${votes.length}件）`),
    overflowVotes.length
      ? el("p", { class: "muted" }, `最新${cardVotes.length}件をカードで表示し、残り${overflowVotes.length}件は定例会ごとの折りたたみに残しています。`)
      : null,
    cardVotes.length
      ? el("div", { class: "member-divided-vote-grid" },
          cardVotes.map(renderDividedVoteCard),
        )
      : el("p", { class: "empty-message is-compact" }, emptyText),
    renderHighlightOverflow(overflowVotes),
  ]);
}

function renderDividedVoteCard({ vote, item }) {
  const counts = voteCounts(vote);
  return el("article", { class: "member-divided-vote-card" }, [
    el("div", { class: "member-vote-card-head" }, [
      el("div", { class: "vote-date" }, vote.date || "日付なし"),
      el("h4", {}, vote.bill_title || "議案名なし"),
      renderLargeVoteBadge(item.vote),
    ]),
    el("div", { class: "vote-card-meta" }, [
      el("p", {}, [
        el("span", { class: "detail-label" }, "全体"),
        el("span", {}, formatVoteCounts(counts)),
      ]),
      el("p", {}, [
        el("span", { class: "detail-label" }, "結果"),
        el("span", {}, vote.result || "結果なし"),
      ]),
    ]),
  ]);
}

function renderAllVoteGroups(groups, total) {
  return el("section", { class: "all-vote-records" }, [
    el("h3", {}, `その他の記録（${total}件）`),
    el("p", { class: "muted" }, "全会一致や少数側が小さい議決は、定例会ごとに畳んで残しています。"),
    el("div", { class: "member-vote-session-list" }, groups.map(renderVoteSessionGroup)),
  ]);
}

function renderHighlightOverflow(votes) {
  if (!votes.length) return null;
  return el("details", { class: "highlight-vote-overflow" }, [
    el("summary", {}, `残り${votes.length}件を定例会ごとに見る`),
    el("div", { class: "member-vote-session-list" },
      groupVotesBySession(votes).map(renderVoteSessionGroup),
    ),
  ]);
}

function renderVoteSessionGroup(group) {
  return el("details", { class: "member-vote-session" }, [
    el("summary", {}, `${group.label}（${group.items.length}件）`),
    el("div", { class: "member-vote-table" },
      group.items.map(renderCompactMemberVoteRow),
    ),
  ]);
}

function renderCompactMemberVoteRow({ vote, item }) {
  return el("div", { class: "member-vote-row" }, [
    el("span", { class: "vote-date" }, vote.date || "日付なし"),
    el("span", { class: "vote-title" }, vote.bill_title || "議案名なし"),
    renderVoteBadge(item.vote),
    el("span", { class: "vote-summary-result" }, vote.result || "結果なし"),
  ]);
}

function renderVoteSourceSummary(memberVotes) {
  const sources = uniqueSourceUrls(memberVotes);
  if (!sources.length) return null;
  const first = sources[0];
  return el("p", { class: "section-source" }, [
    "出典: ",
    el("a", { href: first, target: "_blank", rel: "noopener" }, "議員別賛否PDF"),
    sources.length > 1 ? `（ほか${sources.length - 1}件）` : "",
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

function renderLargeVoteBadge(value) {
  return el("div", {
    class: `member-vote-large ${voteClass(value)}`,
    title: voteHelpText(value),
  }, [
    el("span", { class: "member-vote-symbol" }, voteSymbol(value)),
    el("span", { class: "member-vote-large-label" }, voteDisplayText(value)),
  ]);
}

function memberVoteCounts(memberVotes) {
  const counts = {};
  for (const { item } of memberVotes || []) {
    const value = item.vote || "不明";
    counts[value] = (counts[value] || 0) + 1;
  }
  return counts;
}

function voteCounts(vote) {
  const counts = {};
  for (const entry of vote.votes_by_member || []) {
    const value = entry.vote || "不明";
    counts[value] = (counts[value] || 0) + 1;
  }
  return counts;
}

function categorizeMemberVotes(memberVotes) {
  const minorityVotes = [];
  const broadSplitVotes = [];
  const otherVotes = [];
  for (const entry of memberVotes || []) {
    if (isMemberMinorityVote(entry)) {
      minorityVotes.push(entry);
      continue;
    }
    if (isBroadlySplitVote(entry.vote)) {
      broadSplitVotes.push(entry);
      continue;
    }
    otherVotes.push(entry);
  }
  return { minorityVotes, broadSplitVotes, otherVotes };
}

function isMemberMinorityVote({ vote, item }) {
  if (item.vote !== "賛成" && item.vote !== "反対") return false;
  const counts = voteCounts(vote);
  const ownCount = counts[item.vote] || 0;
  const otherCount = item.vote === "賛成"
    ? counts["反対"] || 0
    : counts["賛成"] || 0;
  // 本人の賛成/反対が、もう一方の票数より少ない場合だけ「少数派側」と扱う。
  // 同数や議長・除斥などは解釈を足さず、定例会ごとの記録に残す。
  return ownCount > 0 && ownCount < otherCount;
}

function isBroadlySplitVote(vote) {
  const counts = voteCounts(vote);
  const yes = counts["賛成"] || 0;
  const no = counts["反対"] || 0;
  const presentVotes = yes + no;
  if (!yes || !no || !presentVotes) return false;

  // 「大きく分かれた」は、少数側が賛成/反対投票者のおおむね3割以上を占める議決とする。
  return Math.min(yes, no) / presentVotes >= SPLIT_VOTE_THRESHOLD;
}

function formatVoteCounts(counts) {
  const ordered = [
    ...VOTE_ORDER.filter((key) => counts[key]),
    ...Object.keys(counts).filter((key) => !VOTE_ORDER.includes(key)).sort((a, b) => a.localeCompare(b, "ja")),
  ];
  return ordered.length
    ? ordered.map((key) => `${key}${counts[key]}`).join(" / ")
    : "記録なし";
}

function groupVotesBySession(memberVotes) {
  const groups = new Map();
  for (const item of memberVotes || []) {
    const label = sessionLabel(item.vote);
    if (!groups.has(label)) groups.set(label, []);
    groups.get(label).push(item);
  }
  return [...groups.entries()].map(([label, items]) => ({ label, items }));
}

function sessionLabel(vote) {
  if (vote?.session) return vote.session;
  const dateValue = vote?.date;
  const match = String(dateValue || "").match(/^(\d{4})-(\d{2})-/);
  if (!match) return "日付なし";
  const year = Number(match[1]);
  const month = Number(match[2]);
  if (!year || !month) return "日付なし";
  if (year >= 2019) return `令和${year - 2018}年${month}月定例会`;
  return `${year}年${month}月定例会`;
}

function uniqueSourceUrls(memberVotes) {
  const urls = [];
  const seen = new Set();
  for (const { vote } of memberVotes || []) {
    const url = vote.source_url;
    if (!url || seen.has(url)) continue;
    seen.add(url);
    urls.push(url);
  }
  return urls;
}

function voteDisplayText(value) {
  if (value === "議長") return "議長（採決に加わらず）";
  if (value === "除斥") return "除斥";
  return value || "不明";
}

function voteSymbol(value) {
  if (value === "賛成") return "○";
  if (value === "反対") return "×";
  if (value === "議長") return "議";
  if (value === "除斥") return "除";
  return "・";
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

function voteMissingMessage(council) {
  if (council?.id === "tottori-city") {
    return "賛否PDFが機械可読でない形式のため未収録です（対応検討中）。";
  }
  if (council?.id === "yonago-city") {
    return "議員別の賛否は公式に公開されていません（議決結果のみ）。";
  }
  return "議員別賛否データはまだ取得していません。";
}
