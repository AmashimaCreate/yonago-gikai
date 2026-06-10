const cache = new Map();

async function loadJson(path, { optional = false } = {}) {
  if (cache.has(path)) return cache.get(path);
  const res = await fetch(path, { cache: "no-cache" });
  if (!res.ok) {
    if (optional && res.status === 404) {
      cache.set(path, null);
      return null;
    }
    throw new Error(`${path}: ${res.status}`);
  }
  const data = await res.json();
  cache.set(path, data);
  return data;
}

export async function loadCouncils() {
  const data = await loadJson("./data/councils.json");
  return Array.isArray(data.councils) ? data.councils : [];
}

export async function loadCouncilBundle(councilId, { includeSpeeches = false } = {}) {
  const councils = await loadCouncils();
  const council = councils.find((item) => item.id === councilId);
  if (!council) throw new Error(`議会が見つかりません: ${councilId}`);

  const [membersMeta, profile, speechesMeta] = await Promise.all([
    loadJson(`./data/${councilId}/members.json`),
    loadJson(`./data/${councilId}/profile.json`, { optional: true }),
    includeSpeeches
      ? loadJson(`./data/${councilId}/speeches.json`, { optional: true })
      : Promise.resolve(null),
  ]);

  return {
    council,
    membersMeta,
    members: Array.isArray(membersMeta.members) ? membersMeta.members : [],
    profile,
    speechesMeta,
    speeches: speechesMeta && Array.isArray(speechesMeta.speeches)
      ? speechesMeta.speeches
      : [],
  };
}
