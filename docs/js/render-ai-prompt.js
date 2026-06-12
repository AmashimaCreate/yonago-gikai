import { el } from "./utils.js";

const AI_LINK_URL_LIMIT = 2000;
const AI_SERVICES = [
  {
    key: "chatgpt",
    label: "ChatGPTで開く",
    url: (encoded) => `https://chatgpt.com/?q=${encoded}`,
    acceptsPrompt: true,
  },
  {
    key: "claude",
    label: "Claudeで開く",
    url: (encoded) => `https://claude.ai/new?q=${encoded}`,
    acceptsPrompt: true,
  },
  {
    key: "perplexity",
    label: "Perplexityで開く",
    url: (encoded) => `https://www.perplexity.ai/search?q=${encoded}`,
    acceptsPrompt: true,
  },
  {
    key: "gemini",
    label: "Geminiを開く",
    url: () => "https://gemini.google.com/app",
    acceptsPrompt: false,
  },
];

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
    renderAiServiceLinks(prompt),
    textarea,
    status,
    el("p", { class: "ai-caution" }, "AIの回答には誤りが含まれることがあります。重要な判断は一次ソースで確認してください。"),
  ]);
}

function renderAiServiceLinks(prompt) {
  const links = aiServiceLinks(prompt);
  if (!links.length) {
    return el("p", { class: "ai-link-note" }, "プロンプトが長いため、外部サービスへの直接リンクは表示していません。コピーして貼り付けてください。");
  }

  return el("div", { class: "ai-service-links" }, [
    el("div", { class: "ai-service-button-row" }, links.map((link) =>
      el("a", {
        class: `ai-service-link is-${link.key}`,
        href: link.url,
        target: "_blank",
        rel: "noopener noreferrer",
        title: link.note || undefined,
      }, link.label),
    )),
    el("p", { class: "ai-link-note" }, [
      "リンク先は外部サービスです。ログインが必要な場合があります。",
      " ",
      el("span", {}, "Geminiはコピーして貼り付けてください。"),
    ]),
  ]);
}

export function aiServiceLinks(prompt) {
  const encoded = encodeURIComponent(prompt);
  const links = AI_SERVICES.map((service) => {
    const url = service.url(encoded);
    return {
      key: service.key,
      label: service.label,
      url,
      note: service.acceptsPrompt ? "" : "プロンプト受け渡しに未対応のため、コピーして貼り付けてください",
    };
  });
  return links.some((link) => link.url.length > AI_LINK_URL_LIMIT) ? [] : links;
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
