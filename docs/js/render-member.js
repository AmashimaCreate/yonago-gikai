import { acquisitionText, cautionNote, coverageText, sourceLink } from "./data-quality.js?v=20260614-finance-compact";
import { councilAreaName, officialCouncilUrl, renderAiPromptCard } from "./render-ai-prompt.js?v=20260614-finance-compact";
import { hasMemberVoteLayer, renderMemberVoteSection } from "./render-votes.js?v=20260614-finance-compact";
import { el } from "./utils.js?v=20260614-finance-compact";

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
  root.appendChild(renderMemberResearchSection(member, state));
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

function renderMemberResearchSection(member, state) {
  const council = state.currentCouncil;
  return el("details", { class: "research-section member-research-details page-card" }, [
    el("summary", {}, [
      el("span", { class: "eyebrow" }, "もっと調べる"),
      el("strong", {}, "AIに聞いてみる"),
      el("small", {}, "質問の雛形を開く"),
    ]),
    renderAiPromptCard({
      title: "AIに聞いてみる",
      lead: "目的に合わせた質問の雛形を用意しました",
      prompts: memberPromptItems(member, state),
    }),
  ]);
}

function memberPromptItems(member, state) {
  const council = state.currentCouncil;
  const prompts = [
    {
      key: "activity",
      label: "活動テーマ",
      text: structuredPrompt(member.name, council, activityInstruction(member, council)),
    },
  ];
  if (hasMemberVoteLayer(council, state.votesMeta, state.votes)) {
    prompts.push({
      key: "votes",
      label: "賛否の傾向",
      text: structuredPrompt(member.name, council, voteTendencyInstruction(member, state)),
    });
  }
  prompts.push({
    key: "profile",
    label: "経歴・基本情報",
    text: structuredPrompt(member.name, council, profileInstruction(member, council)),
  });
  return prompts;
}

function structuredPrompt(target, council, instruction) {
  return [
    `対象: ${target}(${council?.name || "議会"})`,
    "# お願い",
    `- ${instruction}`,
    "- 専門用語にはひとこと説明を添えてください",
    "- 確実でない点や古い可能性のある点は「分からない」と述べ、できれば出典を示してください",
    "- 評価や良し悪しの断定ではなく、事実の整理をお願いします",
  ].join("\n");
}

function activityInstruction(member, council) {
  const prefectureName = council?.prefecture_name || "鳥取県";
  const councilName = council?.name || "議会";
  const minutesUrl = council?.minutes_base_url;
  if (minutesUrl) {
    return `${prefectureName}の${councilName}議員・${member.name}さんについて、${councilName}の会議録検索システム(${minutesUrl})で最近の発言を検索し、どんなテーマについて発言しているか事実ベースで整理してください`;
  }
  const officialUrl = officialCouncilUrl(council);
  return `${prefectureName}の${councilName}議員・${member.name}さんについて、${councilName}の公式サイト(${officialUrl})で公開情報を確認し、最近どんなテーマに関わっているか事実ベースで整理してください`;
}

function voteTendencyInstruction(member, state) {
  const council = state.currentCouncil;
  const sourceUrl = council?.votes_official_url || firstVoteSourceUrl(state.votes) || officialCouncilUrl(council);
  return `${council?.name || "議会"}の議決結果(議員別賛否PDF: ${sourceUrl})をもとに、${member.name}議員が少数派に回った議決にどんな傾向があるか、事実ベースで整理してください`;
}

function profileInstruction(member, council) {
  const faction = member.faction || "会派データなし";
  const committees = Array.isArray(member.committees) && member.committees.length
    ? `担当委員会: ${member.committees.join(" / ")}。`
    : "";
  const profileUrl = member.official_profile_url || officialCouncilUrl(council);
  return `${member.name}議員(${council?.name || "議会"}、${faction})の経歴や担当委員会など公開されている基本情報を、出典(${profileUrl})を示しながら整理してください。${committees}`;
}

function firstVoteSourceUrl(votes) {
  return (votes || []).find((vote) => vote.source_url)?.source_url || "";
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
