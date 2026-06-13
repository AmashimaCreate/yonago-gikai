// 共有状態。各モジュールが import { state } で参照する。
// ES Modules のインポート束縛はライブ参照のため、複数モジュール間で
// 同一オブジェクトを共有できる。
export const state = {
  route: { name: "top" },
  councils: [],
  currentCouncil: null,
  members: [],
  membersMeta: null,
  profile: null,
  timeseries: null,
  finance: null,
  councilSummaries: [],
  speeches: [],
  speechesMeta: null,
  votes: [],
  votesMeta: null,
  councilSection: "area",
  view: "kaiha",
  query: "",
};
