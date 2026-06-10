export function parseRoute(hash = window.location.hash) {
  const raw = hash.replace(/^#/, "") || "/";
  const parts = raw.split("/").filter(Boolean).map(decodeURIComponent);

  if (parts.length === 0) return { name: "top" };
  if (parts[0] !== "councils") return { name: "not-found" };
  if (!parts[1]) return { name: "not-found" };
  if (parts.length === 2) {
    return { name: "council", councilId: parts[1] };
  }
  if (parts[2] === "members" && parts[3]) {
    return {
      name: "member",
      councilId: parts[1],
      memberId: parts[3],
    };
  }
  return { name: "not-found" };
}

export function topPath() {
  return "#/";
}

export function councilPath(councilId) {
  return `#/councils/${encodeURIComponent(councilId)}`;
}

export function memberPath(councilId, memberId) {
  return `${councilPath(councilId)}/members/${encodeURIComponent(memberId)}`;
}
