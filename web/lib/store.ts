"use client";
// 화면 상태. app/main.py 의 S(st.session_state)와 같은 이름·같은 규칙.
// 작은 전역 저장소: getState()/set() + useStore() (useSyncExternalStore).
import { useSyncExternalStore } from "react";
import { api, isError } from "./api";
import type { Ask, ChatOut, Detail, Food, Help, PlaceResult, Recommend } from "./api";

export type Screen = "home" | "result" | "food" | "answer";
export const TABS = ["한눈에", "코스", "식당", "병원·약국"] as const;
export type Tab = (typeof TABS)[number];

/** 대화 답에 붙는 가게·병원 단추 */
export interface MsgItem {
  name: string;
  kind: string;
  lat: number;
  lon: number;
  phone?: string;
}

export interface Msg {
  role: "user" | "bot";
  text: string;
  places?: string[];
  trace?: string[];
  items?: MsgItem[];
}

/** 지도를 부드럽게 옮겨 달라는 요청(시작 화면 동네 고르기). all이면 제주 전체. n은 같은 곳을 다시 눌러도 움직이게 */
export interface MapView {
  lat?: number;
  lon?: number;
  level?: number;
  all?: boolean;
  n: number;
}

export interface Pending {
  text: string;
  userType: string | null;
  /** 시작 화면 '찾기': 대화창에 말을 남기지 않고 결과만 보여 준다 */
  silent?: boolean;
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
  focus: string | null; // 지도·패널·대화가 함께 가리키는 가게·병원 이름
  view: MapView | null; // 지도 부드럽게 옮기기
  // 아래는 처음으로 가도 그대로 두는 화면 설정
  checked: Record<string, boolean>; // 질문지 체크(Streamlit 체크박스 key 와 같은 열쇠)
  sheet: "half" | "full"; // 휴대폰 아래 시트 높이
}

function defaults(): Omit<State, "checked" | "sheet"> {
  return {
    history: [], msgs: [], ask: null, results: null, user_type: "other", selected: null,
    big: false, food: null, when: "오늘", shown: [], screen: "home", tab: "한눈에",
    pending: null, detail_only: null, help_only: null,
    chat_open: false, panel_open: true, unread: 0, typing: null, location: null, focus: null, view: null,
  };
}

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
export function go(text: string | null | undefined, userType: string | null = null, openChat = false, silent = false) {
  const t = (text || "").trim();
  if (!t || state.pending) return;
  const pending: Pending = { text: t, userType, silent };
  set((s) => ({
    ...s,
    msgs: silent ? s.msgs : [...s.msgs, { role: "user", text: t }],
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
  s.focus = null;
  const names: string[] = [];
  let items: MsgItem[] = [];
  let places: string[] = [];
  for (const { name, args, result } of out.tool_results) {
    names.push(name);
    if (name === "get_weather" && args?.when) s.when = String(args.when);
    if (name === "search_food") {
      s.food = result as Food;
      items = (s.food.items ?? []).slice(0, 3).map((it) => ({ name: it.name, kind: it.food_type, lat: it.lat, lon: it.lon, phone: it.phone }));
    }
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
    if (name === "find_nearby_help" && !isError(result)) {
      s.help_only = result as Help;
      const asked: string[] = (args?.kinds as string[] | undefined) ?? ["약국", "병·의원", "응급실"];
      items = asked.flatMap((k) => (s.help_only?.help?.[k] ?? []).map((it) => ({
        name: it.name, kind: k, lat: it.lat, lon: it.lon, phone: it.phone,
      }))).slice(0, 3);
      const said = firstMentioned(out.text, items.map((it) => it.name));
      s.focus = said ?? items[0]?.name ?? null; // 답에 나온 병원·약국을 지도에서도 크게
    }
  }
  if (s.food && names.includes("search_food")) {
    // 하르방이 말로 먼저 꺼낸 가게를 목록·지도의 1순위로(말과 화면이 어긋나지 않게)
    const its = s.food.items ?? [];
    const hit = firstMentioned(out.text, its.map((it) => it.name));
    if (hit) {
      s.food = { ...s.food, items: [...its.filter((it) => it.name === hit), ...its.filter((it) => it.name !== hit)] };
      s.focus = hit;
    }
    items = (s.food.items ?? []).slice(0, 3).map((it) => ({ name: it.name, kind: it.food_type, lat: it.lat, lon: it.lon, phone: it.phone }));
  }
  s.ask = out.ask;
  const said = names.includes("recommend_places") ? firstMentioned(out.text, resultNames(s)) : null;
  if (said) {
    // 하르방이 말로 먼저 꺼낸 장소를 대시보드·지도에도 띄운다(말과 화면이 어긋나지 않게)
    s.selected = said;
    places = [said, ...places.filter((x) => x !== said)];
  }
  if (!p.silent) {
    s.msgs = [...s.msgs, {
      role: "bot",
      text: out.text || "찾은 내용을 정리했어요.",
      places,
      items,
    }];
  }
  s.typing = p.silent ? null : s.msgs.length - 1;
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
  if (!s.chat_open && !p.silent) {
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

/** 지도 표식·대화 단추·패널 카드에서 가게·병원을 고르면 셋이 같은 곳을 가리킨다 */
export function focusItem(name: string, fromChat = false) {
  // 휴대폰은 대화창이 화면 전체라 닫아야 지도가 보인다. PC는 대화창 옆에 지도가 보이므로 대화를 그대로 둔다.
  const phone = typeof window !== "undefined" && window.matchMedia("(max-width: 639.98px)").matches;
  set((s) => ({
    ...s,
    focus: name,
    panel_open: true,
    sheet: "half",
    ...(fromChat && phone ? { chat_open: false } : {}),
  }));
}

/** 결과 화면에서 처음 화면으로(대화 기록은 그대로) */
export function backHome() {
  set({ screen: "home", focus: null });
}

/** '내 위치로 찾기': 브라우저 위치를 받아 방금 질문을 다시 보낸다 */
export function locateAndRetry() {
  const lastQ = [...state.history].reverse().find((h) => h.role === "user")?.content ?? "근처 약국 찾아줘";
  const fail = (why: string) => set((s) => ({
    ...s,
    ask: null,
    msgs: [...s.msgs, { role: "bot", text: why }],
  }));
  if (typeof navigator === "undefined" || !navigator.geolocation) {
    fail("이 기기에서는 위치를 가져올 수 없어요. 동네나 장소 이름을 말씀해 주세요.");
    return;
  }
  navigator.geolocation.getCurrentPosition(
    (p) => {
      set({ location: [p.coords.latitude, p.coords.longitude], ask: null });
      go(lastQ, null, true);
    },
    () => fail("위치를 가져오지 못했어요. 위치 권한을 허용하거나 동네 이름을 말씀해 주세요."),
    { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 },
  );
}

/** 시작 화면 '내 위치': 제주 안 좌표만 넣는다(밖이면 null) */
export function setLocation(loc: [number, number] | null) {
  set({ location: loc });
}

export function setMapView(v: Omit<MapView, "n">) {
  set((s) => ({ ...s, view: { ...v, n: (s.view?.n ?? 0) + 1 } }));
}

export function setSheet(sheet: "half" | "full") {
  set({ sheet });
}

export function typingDone() {
  if (state.typing !== null) set({ typing: null });
}
