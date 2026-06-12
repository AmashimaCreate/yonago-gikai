import { el } from "./utils.js";

export function renderAiPromptCard({ title, lead, prompt, compact = false }) {
  const textarea = el("textarea", {
    class: "ai-prompt-text",
    readonly: "",
    rows: compact ? 3 : 5,
  }, prompt);
  const status = el("span", { class: "copy-status", "aria-live": "polite" }, "");
  const button = el("button", {
    type: "button",
    class: "copy-button",
    onclick: () => copyPromptText(prompt, textarea, button, status),
  }, "コピー");

  return el("article", { class: `ai-prompt-card${compact ? " is-compact" : ""}` }, [
    el("div", { class: "ai-prompt-head" }, [
      el("div", {}, [
        el("h3", {}, title),
        lead ? el("p", {}, lead) : null,
      ]),
      button,
    ]),
    textarea,
    status,
    el("p", { class: "ai-caution" }, "AIの回答には誤りが含まれることがあります。重要な判断は一次ソースで確認してください。"),
  ]);
}

async function copyPromptText(text, textarea, button, status) {
  button.disabled = true;
  try {
    await navigator.clipboard.writeText(text);
    status.textContent = "コピーしました";
  } catch {
    textarea.focus();
    textarea.select();
    status.textContent = "コピーできない場合は、選択された本文を手動でコピーしてください";
  } finally {
    window.setTimeout(() => {
      button.disabled = false;
      if (status.textContent === "コピーしました") status.textContent = "";
    }, 1600);
  }
}

export function officialCouncilUrl(council) {
  const links = Array.isArray(council?.official_links) ? council.official_links : [];
  const official = links.find((link) => /公式|ご案内/.test(link.label || ""));
  return official?.url || links[0]?.url || "";
}

export function councilAreaName(council) {
  return (council?.name || "").replace(/議会$/, "").trim();
}
