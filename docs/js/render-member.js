import { acquisitionText, cautionNote, coverageText, sourceLink } from "./data-quality.js";
import { councilPath } from "./router.js";
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

  root.appendChild(
    el("p", { class: "back-link-wrap" }, [
      el("a", { href: councilPath(state.currentCouncil.id) }, `← ${state.currentCouncil.name}へ戻る`),
    ]),
  );

  root.appendChild(renderMemberProfile(member, state.membersMeta));
  root.appendChild(renderSpeechSection(speeches, state.speechesMeta, state.currentCouncil));
}

function renderMemberProfile(member, membersMeta) {
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
        el("p", { class: "quality-inline", title: membersMeta?.acquisition || "" }, acquisitionText(membersMeta)),
        sourceLink(membersMeta?.source_url, "議員名簿の出典"),
      ]),
    ]),
  ]);
}

function renderSpeechSection(speeches, speechesMeta, council) {
  if (!speechesMeta) {
    return el("section", { class: "speech-section" }, [
      el("h2", { class: "section-title" }, "発言インデックス未取得"),
      el("p", { class: "muted" }, coverageText(speechesMeta, council)),
    ]);
  }

  return el("section", { class: "speech-section" }, [
    el("h2", { class: "section-title" }, `発言インデックス（${speeches.length}件）`),
    cautionNote(),
    el("p", { class: "muted" }, coverageText(speechesMeta, council)),
    speeches.length
      ? el("ul", { class: "speech-list" }, speeches.map(renderSpeechItem))
      : el("p", { class: "empty-message" }, "この取得範囲では、この議員に紐付いた発言インデックスはありません。"),
  ]);
}

function renderSpeechItem(speech) {
  return el("li", { class: "speech-item" }, [
    el("div", { class: "speech-date" }, speech.date || "日付なし"),
    el("div", { class: "speech-main" }, [
      el("div", { class: "speech-meeting" }, speech.meeting_name || "会議名なし"),
      el("div", { class: "speech-speaker" }, `発言者表記: ${speech.speaker_label || "データなし"}`),
      sourceLink(speech.source_url, "発言の確認はこちら"),
    ]),
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
