import { acquisitionText, cautionNote, coverageText, sourceLink } from "./data-quality.js";
import { councilAreaName, officialCouncilUrl, renderAiPromptCard } from "./render-ai-prompt.js";
import { renderMemberVoteSection } from "./render-votes.js";
import { el } from "./utils.js";

export function renderMemberPage(root, state, memberId) {
  const member = state.members.find((item) => item.id === memberId);
  root.innerHTML = "";

  if (!member) {
    root.appendChild(el("p", { class: "empty-message" }, "議員データが見つかりません。"));
    return;
  }

  const speeches = (state.speeches || [])
    .filter((speech) => speech.member_id === member.id)
    .sort((a, b) => (b.date || "").localeCompare(a.date || ""));

  root.appendChild(renderMemberProfile(member, state.membersMeta, state.currentCouncil));
  const voteSection = renderMemberVoteSection(
    state.votes,
    state.votesMeta,
    member,
    state.currentCouncil,
    state.route,
  );
  if (voteSection) root.appendChild(voteSection);
  root.appendChild(renderMemberResearchSection(member, state.currentCouncil));
  root.appendChild(renderSpeechSection(speeches, state.speechesMeta, state.currentCouncil));
}

function renderMemberProfile(member, membersMeta, council) {
  return el("section", { class: "member-detail" }, [
    el("div", { class: "member-detail-main" }, [
      renderPhoto(member),
      el("div", {}, [
        el("h2", {}, member.name),
        el("p", { class: "member-kana" }, member.name_kana || "ふりがな: データなし"),
        detailRow("会派", member.faction || "データなし"),
        detailRow("当選回数", typeof member.elected_count === "number" ? `${member.elected_count}回` : "データなし"),
        detailRow("役職", listText(member.positions)),
        detailRow("委員会", listText(member.committees)),
        member.official_profile_url
          ? el("p", { class: "official-profile-link" }, [
              sourceLink(member.official_profile_url, "公式プロフィールを見る"),
            ])
          : null,
        renderMemberSearchLink(member, council),
        el("p", { class: "quality-inline", title: membersMeta?.acquisition || "" }, acquisitionText(membersMeta)),
        sourceLink(membersMeta?.source_url, "議員名簿の出典"),
      ]),
    ]),
  ]);
}

function renderMemberSearchLink(member, council) {
  const areaName = councilAreaName(council);
  const query = [member.name, areaName, "議員"].filter(Boolean).join(" ");
  const url = `https://www.google.com/search?q=${encodeURIComponent(query)}`;
  return el("p", { class: "member-search-link" }, [
    el("a", { href: url, target: "_blank", rel: "noopener" }, "この議員について検索"),
    el("small", {}, "外部の検索結果に移動します"),
  ]);
}

function renderMemberResearchSection(member, council) {
  return el("section", { class: "research-section page-card" }, [
    el("p", { class: "eyebrow" }, "もっと調べる"),
    el("h2", { class: "section-title" }, "AIに聞いてみる"),
    renderAiPromptCard({
      title: "この議員の活動テーマを整理する",
      lead: "コピーして、普段使っているAIに貼り付けてください。",
      prompt: memberResearchPrompt(member, council),
    }),
  ]);
}

function memberResearchPrompt(member, council) {
  const prefectureName = council?.prefecture_name || "鳥取県";
  const councilName = council?.name || "議会";
  const minutesUrl = council?.minutes_base_url;
  if (minutesUrl) {
    return `${prefectureName}の${councilName}議員・${member.name}さんについて調べています。\n${councilName}の会議録検索システム(${minutesUrl})で最近の発言を検索し、どんなテーマについて発言しているか、事実ベースで整理してください。評価や良し悪しの判断ではなく、活動内容の整理をお願いします。`;
  }
  const officialUrl = officialCouncilUrl(council);
  return `${prefectureName}の${councilName}議員・${member.name}さんについて調べています。\n${councilName}の公式サイト(${officialUrl})で公開情報を確認し、最近どんなテーマに関わっているか、事実ベースで整理してください。評価や良し悪しの判断ではなく、活動内容の整理をお願いします。`;
}

function renderSpeechSection(speeches, speechesMeta, council) {
  if (!speechesMeta) {
    return el("section", { class: "speech-section" }, [
      el("h2", { class: "section-title" }, "発言インデックス未取得"),
      el("p", { class: "muted" }, coverageText(speechesMeta, council)),
    ]);
  }

  return el("section", { class: "speech-section" }, [
    el("div", { class: "section-heading-row" }, [
      el("div", {}, [
        el("p", { class: "eyebrow" }, "本会議での発言"),
        el("h2", { class: "section-title" }, "発言インデックス"),
      ]),
      el("p", { class: "section-count" }, `${speeches.length}件`),
    ]),
    el("p", { class: "member-speech-summary" }, [
      el("strong", {}, `${speeches.length}件`),
      el("span", {}, " — 本会議での議員発言者として取得した記録"),
    ]),
    el("details", { class: "speech-coverage-note" }, [
      el("summary", {}, "取得範囲と注意を見る"),
      cautionNote(),
      el("p", { class: "muted" }, coverageText(speechesMeta, council)),
    ]),
    speeches.length
      ? el("ul", { class: "speech-list" }, speeches.map(renderSpeechItem))
      : el("p", { class: "empty-message" }, "この取得範囲では、この議員に紐付いた発言インデックスはありません。"),
    renderSpeechSourceSummary(speeches),
  ]);
}

function renderSpeechItem(speech) {
  return el("li", { class: "speech-item" }, [
    el("div", { class: "speech-date" }, speech.date || "日付なし"),
    el("div", { class: "speech-main" }, [
      el("div", { class: "speech-meeting" }, speech.meeting_name || "会議名なし"),
      el("div", { class: "speech-speaker" }, `発言者表記: ${speech.speaker_label || "データなし"}`),
    ]),
  ]);
}

function renderSpeechSourceSummary(speeches) {
  const first = (speeches || []).find((speech) => speech.source_url)?.source_url;
  if (!first) return null;
  return el("p", { class: "section-source" }, [
    "出典: ",
    el("a", { href: first, target: "_blank", rel: "noopener" }, "会議録検索入口"),
  ]);
}

function renderPhoto(member) {
  if (!member.photo_url) {
    return el("div", { class: "member-photo-placeholder" }, "写真なし");
  }
  const photo = el("img", {
    class: "member-detail-photo",
    src: member.photo_url,
    alt: member.name,
    loading: "lazy",
    referrerpolicy: "no-referrer",
  });
  photo.addEventListener("error", () => {
    photo.replaceWith(el("div", { class: "member-photo-placeholder" }, "写真なし"));
  });
  return photo;
}

function detailRow(label, value) {
  return el("p", { class: "detail-row" }, [
    el("span", { class: "detail-label" }, label),
    el("span", { class: "detail-value" }, value),
  ]);
}

function listText(values) {
  if (!Array.isArray(values) || values.length === 0) return "データなし";
  return values.join(" / ");
}
