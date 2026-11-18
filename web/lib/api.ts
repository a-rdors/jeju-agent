// FastAPI(server/api.py) 호출. 주소는 모두 상대 경로(/api/...)이고 next.config.ts rewrites가 :8000으로 넘긴다.
// 도구 결과 모양은 app/tools.py 가 돌려주는 dict 그대로다.

export type UserType = "manual_wheelchair" | "electric_wheelchair" | "stroller" | "senior" | "other";

export const USER_TYPES: Record<string, string> = {
  manual_wheelchair: "수동 휠체어",
  electric_wheelchair: "전동 휠체어",
  stroller: "유모차",
  senior: "어르신(보행)",
  other: "기타",
};

export interface Config {
  kakao_js_key: string;
  ai: boolean;
  user_types: Record<string, string>;
  food_kinds: string[];
  diet_needs: Record<string, string>;
}

export type { PlaceDot } from "./types";
import type { PlaceDot } from "./types";

export interface Check {
  item: string;
  status: string;
  known: boolean;
}

interface Access {
  verdict: string;
  verdict_color: string;
  verdict_reason: string;
  checks: Check[];
  source: string;
}

/** recommend_places().results[] */
export interface PlaceResult extends Access {
  place: string;
  where: string;
  score: number;
  slope_level: string;
  slope_say: string;
  route_slope_max_deg: number | null;
  course_m: number;
  minutes: number | null;
  distance_km: number | null;
  accessible_toilet: boolean;
  accessible_parking: string;
  companion_advised: boolean;
  good_points: string[];
  watch_out: string[];
  themes: string | null;
  lat: number;
  lon: number;
  base_date: string;
  /** '코스(제주도 조사)' 또는 '시설(관광공사)' */
  data_kind?: string;
  phone?: string;
  homepage?: string;
}

export interface Recommend {
  user_type: string;
  area_understood: string | null;
  results: PlaceResult[];
  note: string;
}

export interface CoursePoint {
  at_m: number;
  label: string;
  text: string;
  flags: string[];
  lat: number;
  lon: number;
}

/** get_place_detail() (오류가 아니면) */
export interface Detail extends Access {
  place: string;
  where: string;
  course_m: number;
  minutes: number | null;
  slope_level: string;
  slope_say: string;
  companion_advised: boolean;
  key_points: CoursePoint[];
  all_points: CoursePoint[];
  bus_stops?: BusStop[];
  toilets_near?: { name: string; km?: number; m?: number; phone?: string; address?: string }[];
  base_date: string;
  data_kind?: string;
}

/** 제주데이터허브 버스 정류소 기본 정보에서 고른 가까운 정류소(직선거리). */
export interface BusStop {
  name: string;
  local_info: string;
  direction: string;
  m: number;
  walk_min: number;
  lat: number;
  lon: number;
}

export interface HelpItem {
  name: string;
  km: number;
  address: string;
  phone: string;
  detail: string;
  /** 약국: 약국 정보 API로 확인한 영업 상태("영업 중 확인" 또는 "") */
  status?: string;
  source: string;
  lat: number;
  lon: number;
}

export interface Help {
  place: string;
  help: Record<string, HelpItem[]>;
  bus?: BusStop[];
  bus_source?: string;
  note: string;
  error?: string;
}

export interface FoodItem {
  name: string;
  food_type: string;
  km: number | null;
  address: string;
  phone: string;
  wheelchair_entry: boolean;
  access_info: string;
  why: string[];
  open_status: string;
  lat: number;
  lon: number;
}

export interface Food {
  food_kind: string | null;
  diet_needs: string[];
  diet_labels?: string[];
  around: string;
  center?: [number, number] | null;
  items: FoodItem[];
  with_wheelchair_badge?: number;
  call_questions?: string[];
  anchor_not_found?: boolean;
  note: string;
}

export interface NearbyItem {
  category: string;
  name: string;
  km: number | null;
  phone: string;
  wheelchair_entry: boolean;
  accessible_toilet: boolean;
  open_status: string;
}

export interface Nearby {
  place: string;
  items: NearbyItem[];
  note: string;
}

export interface Weather {
  available?: boolean;
  where?: string;
  date?: string;
  rain_chance?: number | null;
  rain_mm?: number | null;
  wind_ms?: number | null;
  temp?: string;
  is_rainy?: boolean;
  tips?: string[];
  note?: string;
  source?: string;
}

export interface Ask {
  question: string;
  options?: unknown[];
}

export interface ToolResult {
  name: string;
  args: Record<string, unknown>;
  result: unknown;
}

export interface ChatOut {
  text: string;
  ask: Ask | null;
  tool_results: ToolResult[];
  trace: { tool: string; args?: unknown }[];
  fallback: boolean;
}

export interface ChatBody {
  text: string;
  user_type?: string | null;
  history: { role: string; content: string }[];
  known_user_type?: string | null;
  last_place?: string | null;
  location?: [number, number] | null;
  shown_places?: string[];
}

/** 도구 결과에 error 가 있으면 true */
export function isError(x: unknown): x is { error: string } {
  return typeof x === "object" && x !== null && "error" in x;
}

function qs(o: Record<string, string>) {
  return new URLSearchParams(o).toString();
}

/** GET 주소. useApi(주소)로 쓰면 같은 주소는 한 번만 불러온다. */
export const urls = {
  config: "/api/config",
  places: "/api/places",
  detail: (place: string, userType: string) => `/api/detail?${qs({ place, user_type: userType })}`,
  help: (place: string) => `/api/help?${qs({ place })}`,
  food: (place: string, wheel: boolean) => `/api/food?${qs({ place, wheel: String(wheel) })}`,
  nearby: (place: string) => `/api/nearby?${qs({ place })}`,
  weather: (place: string, when: string) => `/api/weather?${qs({ place, when })}`,
  questions: (userType: string, dietNeeds?: string[] | null) =>
    `/api/questions?${qs(dietNeeds && dietNeeds.length ? { user_type: userType, diet_needs: dietNeeds.join(",") } : { user_type: userType })}`,
  routeLink: (name: string, lat: number, lon: number) => `/api/route-link?${qs({ name, lat: String(lat), lon: String(lon) })}`,
};

export async function getJSON<T>(url: string): Promise<T> {
  const r = await fetch(url, { headers: { Accept: "application/json" } });
  if (!r.ok) throw new Error(`${r.status} ${url}`);
  return (await r.json()) as T;
}

export const api = {
  config: () => getJSON<Config>(urls.config),
  places: () => getJSON<PlaceDot[]>(urls.places),
  detail: (place: string, userType: string) => getJSON<Detail | { error: string }>(urls.detail(place, userType)),
  help: (place: string) => getJSON<Help>(urls.help(place)),
  food: (place: string, wheel: boolean) => getJSON<Food>(urls.food(place, wheel)),
  nearby: (place: string) => getJSON<Nearby>(urls.nearby(place)),
  weather: (place: string, when: string) => getJSON<Weather>(urls.weather(place, when)),
  questions: (userType: string, dietNeeds?: string[] | null) => getJSON<string[]>(urls.questions(userType, dietNeeds)),
  routeLink: (name: string, lat: number, lon: number) => getJSON<{ url: string }>(urls.routeLink(name, lat, lon)),
  async chat(body: ChatBody): Promise<ChatOut> {
    const r = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(`${r.status} /api/chat`);
    return (await r.json()) as ChatOut;
  },
};

/** tools.kakao_route_link 와 같은 규칙: quote(name, safe='') 는 !'()* 도 바꾼다. */
export function kakaoRouteLink(name: string, lat: number, lon: number) {
  const enc = encodeURIComponent(String(name)).replace(/[!'()*]/g, (c) => "%" + c.charCodeAt(0).toString(16).toUpperCase());
  return `https://map.kakao.com/link/to/${enc},${lat},${lon}`;
}
