"use client";
// 화면 상태. app/main.py 의 S(st.session_state)와 같은 이름·같은 규칙.
// 작은 전역 저장소: getState()/set() + useStore() (useSyncExternalStore).
import { useSyncExternalStore } from "react";
import { api, isError } from "./api";
import type { Ask, ChatOut, Detail, Food, Help, PlaceResult, Recommend } from "./api";

export type Screen = "home" | "result" | "food" | "answer";
export const TABS = ["한눈에", "코스", "식당", "병원·약국"] as const;
export type Tab = (typeof TABS)[number];

export interface Msg {
  role: "user" | "bot";
  text: string;
  places?: string[];
  trace?: string[];
}

export interface Pending {
  text: string;
  userType: string | null;
}

export interface State {
  history: { role: "user" | "assistant"; content: string }[];
  msgs: Msg[];
  ask: Ask | null;
  results: Recommend | null;
  user_type: string;
  selected: string | null;
  big: boolean;
  food: Food | null;
  when: string;
  shown: string[];
  screen: Screen;
  tab: Tab;
  pending: Pending | null;
  detail_only: Detail | null;
  help_only: Help | null;
  chat_open: boolean;
  panel_open: boolean;
  unread: number;
  typing: number | null;
  location: [number, number] | null; // (위도, 경도). 위치 권한을 받으면 채운다
  // 아래는 처음으로 가도 그대로 두는 화면 설정
  checked: Record<string, boolean>; // 질문지 체크(Streamlit 체크박스 key 와 같은 열쇠)
  sheet: "half" | "full"; // 휴대폰 아래 시트 높이
}

function defaults(): Omit<State, "checked" | "sheet"> {
  return {
    history: [], msgs: [], ask: null, results: null, user_type: "other", selected: null,
    big: false, food: null, when: "오늘", shown: [], screen: "home", tab: "한눈에",
    pending: null, detail_only: null, help_only: null,
    chat_open: false, panel_open: true, unread: 0, typing: null, location: null,
  };
}

// 대화 답 아래 '찾아본 정보' 한 줄에 쓰는 이름(되묻기는 보여 주지 않는다)
export const STEP_NAMES: Record<string, string> = {
  recommend_places: "갈 만한 곳", get_weather: "날씨",
  search_food: "식당", get_place_detail: "코스·시설",
  find_nearby_help: "병원·약국", check_nearby_places: "주변 가게",
  plan_outing: "나들이 일정", ask_user: "",
};

const INITIAL: State = { ...defaults(), checked: {}, sheet: "half" };
let state: State = INITIAL;
const listeners = new Set<() => void>();

/** 대시보드에 보일 내용이 없으면 시작 화면(main.py dashboard()의 S.screen = "home") */
function normalize(s: State): State {
  const ok =
    s.screen === "home" ||
    (s.screen === "result" && !!s.results) ||
    (s.screen === "food" && !!s.food) ||
    (s.screen === "answer" && !!(s.detail_only || s.help_only));
  return ok ? s : { ...s, screen: "home" };
}

export function getState() {
  return state;
}

function set(patch: Partial<State> | ((s: State) => State)) {
  const next = typeof patch === "function" ? patch(state) : { ...state, ...patch };
  state = normalize(next);
  listeners.forEach((l) => l());
}

export function useStore(): State {
  return useSyncExternalStore(
    (l) => {
      listeners.add(l);
      return () => {
        listeners.delete(l);
      };
    },
    () => state,
    () => INITIAL,
  );
}

// ---------- 고르기 ----------
export function resultNames(s: State): string[] {
  return (s.results?.results ?? []).map((r) => r.place);
}

export function topPlace(s: State): PlaceResult | null {
  const res = s.results?.results ?? [];
  return res.find((r) => r.place === s.selected) ?? res[0] ?? null;
}

/** 답변 글에서 가장 먼저 나온 장소 이름. 같은 자리에서 시작하면 긴 이름. */
export function firstMentioned(text: string, names: string[]): string | null {
  const t = text || "";
  const hits = names
    .filter((n) => n && t.includes(n))
    .map((n) => [t.indexOf(n), -n.length, n] as const)
    .sort((a, b) => a[0] - b[0] || a[1] - b[1] || (a[2] < b[2] ? -1 : a[2] > b[2] ? 1 : 0));
  return hits.length ? hits[0][2] : null;
}

export function conditionTexts(s: State, userTypes: Record<string, string>): string[] {
  const bits: string[] = [];
  if (s.user_type !== "other") bits.push(userTypes[s.user_type] ?? s.user_type);
  if (s.food?.diet_labels?.length) bits.push(s.food.diet_labels.join(" · "));
  bits.push(s.when);
  const where = s.results?.area_understood;
  if (where) bits.push(`${where} 기준`);
  return bits;
}

// ---------- 동작 ----------
/** 버튼·입력창. 사용자 말은 바로 보이고, 답은 기다렸다가 받는다(대화창에는 '입력 중' 표시). */
export function go(text: string | null | undefined, userType: string | null = null, openChat = false) {
  const t = (text || "").trim();
  if (!t || state.pending) return;
  const pending: Pending = { text: t, userType };
  set((s) => ({
    ...s,
    msgs: [...s.msgs, { role: "user", text: t }],
    pending,
    ...(openChat ? { chat_open: true, unread: 0 } : {}),
  }));
  void process(pending);
}

async function process(pending: Pending) {
  const s = state;
  const known = s.user_type !== "other" ? s.user_type : null;
  let out: ChatOut | null = null;
  try {
    out = await api.chat({
      text: pending.text,
      user_type: pending.userType,
      history: [...s.history, { role: "user", content: pending.text }],
      known_user_type: known,
      last_place: s.selected,
      location: s.location,
      shown_places: s.shown,
    });
  } catch {
    out = null;
  }
  if (state.pending !== pending) return; // 그사이 '처음으로'를 눌렀으면 버린다
  let next: State;
  try {
    next = out ? send(state, pending, out) : failed(state, pending);
  } catch {
    next = failed(state, pending);
  }
  set({ ...next, pending: null });
}

function failed(s0: State, p: Pending): State {
  const msgs: Msg[] = [...s0.msgs, { role: "bot", text: "찾는 중에 문제가 생겼어요. 한 번 더 말씀해 주세요.", places: [], trace: [] }];
  return {
    ...s0,
    history: [...s0.history, { role: "user", content: p.text }],
    msgs,
    typing: s0.chat_open ? msgs.length - 1 : null,
    unread: s0.chat_open ? s0.unread : s0.unread + 1,
  };
}

/** main.py send() 뒷부분: 도구 결과로 상태를 바꾸고 대시보드에 보일 내용을 정한다. */
function send(s0: State, p: Pending, out: ChatOut): State {
  const s: State = { ...s0 };
  if (p.userType) s.user_type = p.userType;
  s.history = [...s.history, { role: "user", content: p.text }];
  s.ask = null;
  s.detail_only = null;
  s.help_only = null;
  const names: string[] = [];
  let places: string[] = [];
  for (const { name, args, result } of out.tool_results) {
    names.push(name);
    if (name === "get_weather" && args?.when) s.when = String(args.when);
    if (name === "search_food") s.food = result as Food;
    if (name === "recommend_places") {
      const res = result as Recommend;
      const got = (res.results ?? []).map((r) => r.place);
      s.results = res;
      s.food = null;
      s.selected = got[0] ?? null;
      s.shown = [...new Set([...s.shown, ...got])];
      places = got;
      if (args?.user_type) s.user_type = String(args.user_type);
    }
    if (name === "get_place_detail" && !isError(result)) {
      const d = result as Detail;
      if (resultNames(s).includes(d.place)) {
        s.selected = d.place;
        s.detail_only = null;
      } else {
        s.detail_only = d;
      }
      places = places.length ? places : [d.place];
    }
    if (name === "find_nearby_help" && !isError(result)) s.help_only = result as Help;
  }
  s.ask = out.ask;
  const said = names.includes("recommend_places") ? firstMentioned(out.text, resultNames(s)) : null;
  if (said) {
    // 하르방이 말로 먼저 꺼낸 장소를 대시보드·지도에도 띄운다(말과 화면이 어긋나지 않게)
    s.selected = said;
    places = [said, ...places.filter((x) => x !== said)];
  }
  s.msgs = [...s.msgs, {
    role: "bot",
    text: out.text || "찾은 내용을 정리했어요.",
    places,
    trace: (out.trace ?? []).map((t) => STEP_NAMES[t.tool] ?? t.tool),
  }];
  s.typing = s.msgs.length - 1;
  s.history = [...s.history, { role: "assistant", content: out.text }];

  // 대시보드 내용 고르기(그 밖의 대답이면 대시보드는 그대로 두고 대화창에만 답한다)
  const hasResults = resultNames(s).length > 0;
  if (s.ask) {
    s.chat_open = true;
  } else if (names.includes("recommend_places")) {
    s.screen = "result";
    s.tab = "한눈에";
  } else if (names.includes("search_food")) {
    if (hasResults && s.food?.around === s.selected) {
      s.screen = "result";
      s.tab = "식당";
    } else {
      s.screen = "food";
    }
  } else if (names.includes("find_nearby_help") && hasResults && s.help_only && s.help_only.place === s.selected) {
    s.screen = "result";
    s.tab = "병원·약국";
    s.help_only = null;
  } else if (names.includes("get_place_detail") && hasResults && !s.detail_only) {
    s.screen = "result";
    s.tab = "코스";
  } else if (s.detail_only || s.help_only) {
    s.screen = "answer";
  }
  if (!s.chat_open) {
    s.unread += 1;
    s.typing = null; // 닫힌 대화창은 한 글자씩 보여 주지 않는다
  }
  return s;
}

export function toggleChat() {
  set((s) => ({ ...s, chat_open: !s.chat_open, unread: s.chat_open ? s.unread : 0, typing: s.chat_open ? null : s.typing }));
}

export function closeChat() {
  if (state.chat_open) toggleChat();
}

export function togglePanel() {
  set((s) => ({ ...s, panel_open: !s.panel_open }));
}

export function setTab(tab: Tab) {
  set({ tab });
}

/** 이전 후보의 식당 결과는 버린다 */
export function pick(place: string) {
  set({ selected: place, food: null });
}

/** 대화 속 장소 단추·지도 표식을 누르면 그 장소를 대시보드와 지도에 띄운다. */
export function showPlace(place: string) {
  set((s) => {
    let n: State = { ...s };
    if (resultNames(s).includes(place)) {
      n = { ...n, selected: place, food: null, screen: "result", tab: "한눈에" };
    } else if (s.detail_only && s.detail_only.place === place) {
      n.screen = "answer";
    }
    n.panel_open = true;
    return n;
  });
}

/**
 * 지도 장소 카드의 '자세히 살펴보기'. 추천 결과에 있는 곳이면 그 결과를, 아니면 AI 없이 코스 정보를 받아
 * 패널(장소 정보)에 띄운다. 실패하면 하르방에게 물어보는 길로 넘긴다.
 */
export async function lookPlace(place: string) {
  if (resultNames(getState()).includes(place)) {
    showPlace(place);
    return;
  }
  try {
    const d = await api.detail(place, getState().user_type);
    if (isError(d)) throw new Error(d.error);
    set((s) => ({ ...s, detail_only: d, help_only: null, screen: "answer", panel_open: true }));
  } catch {
    go(`${place} 코스 자세히 알려줘`, null, true);
  }
}

export function toResult() {
  set({ screen: "result" });
}

/** 처음으로. 큰 글씨·패널 열림(과 질문지 체크, 시트 높이)은 그대로 둔다. */
export function home() {
  set((s) => ({ ...defaults(), big: s.big, panel_open: s.panel_open, checked: s.checked, sheet: s.sheet }));
}

export function setBig(big: boolean) {
  set({ big });
}

export function setChecked(key: string, on: boolean) {
  set((s) => ({ ...s, checked: { ...s.checked, [key]: on } }));
}

export function setSheet(sheet: "half" | "full") {
  set({ sheet });
}

export function typingDone() {
  if (state.typing !== null) set({ typing: null });
}
