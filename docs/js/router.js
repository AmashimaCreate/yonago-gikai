export function parseRoute(hash = window.location.hash) {
  const raw = hash.replace(/^#/, "") || "/";
  const parts = raw.split("/").filter(Boolean).map(decodeURIComponent);

  if (parts.length === 0) return { name: "national" };

  if (parts[0] === "about" && parts.length === 1) {
    return { name: "about" };
  }

  if (parts[0] === "councils" && parts[1]) {
    const to = parts[2] === "members" && parts[3]
      ? memberPath("tottori", parts[1], parts[3])
      : councilPath("tottori", parts[1]);
    return { name: "redirect", to };
  }

  if (parts[0] !== "pref" || !parts[1]) return { name: "not-found" };
  const prefecture = parts[1];
  if (parts.length === 2) return { name: "prefecture", prefecture };
  if (parts[2] !== "councils" || !parts[3]) return { name: "not-found" };
  if (parts.length === 4) {
    return { name: "council", prefecture, councilId: parts[3] };
  }
  if (parts[4] === "members" && parts[5]) {
    return {
      name: "member",
      prefecture,
      councilId: parts[3],
      memberId: parts[5],
    };
  }
  return { name: "not-found" };
}

export function topPath() {
  return "#/";
}

export function prefPath(prefecture) {
  return `#/pref/${encodeURIComponent(prefecture)}`;
}

export function aboutPath() {
  return "#/about";
}

export function councilPath(prefecture, councilId) {
  return `${prefPath(prefecture)}/councils/${encodeURIComponent(councilId)}`;
}

export function memberPath(prefecture, councilId, memberId) {
  return `${councilPath(prefecture, councilId)}/members/${encodeURIComponent(memberId)}`;
}
