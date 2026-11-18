/**
 * mapData.ts — buildMapData() / legendItems() 순수 함수.
 * Python app/map_view.py 의 build() 와 legend_items() 를 그대로 옮긴 것이다.
 * React 에 의존하지 않으며 서버와 클라이언트 모두에서 사용할 수 있다.
 */
/* eslint-disable @typescript-eslint/no-explicit-any */
import type { MapData, MapMark, PlaceDot } from "./types";

// ── 색 상수 (Python map_view.py / ui.py 와 같은 값) ───────────────────────────
export const VERDICT_HEX: Record<string, string> = {
  green: "#2F7A4D",
  orange: "#2C6EA6",
  gray: "#6B7075",
};

export const CAUTION_HEX = "#B83227";
// 색은 종류마다 다르게: 추천 장소=판정색(초록·주황·회색), 코스=파랑, 화장실=청록, 조심할 곳=빨강
export const ROUTE_HEX = "#2F6FD6";
export const DOT_HEX = "#2F7A4D";
export const TOILET_HEX = "#0E8A8A";
export const FOOD_HEX = "#E07A1C";
export const HELP_HEX = "#5B3A8C";

/** 지도 위험 표시에서 제외할 접근성 항목 (화장실·주차는 경고가 아니라 정보) */
export const NOT_CAUTION: Set<string> = new Set(["장애인 화장실", "장애인 주차", "넓은 화장실", "주차장"]);

// ── 내부 상수 ─────────────────────────────────────────────────────────────────
// 지도 표식 그림(글자 대신 한눈에 알아보는 그림)
const HELP_SHORT: Record<string, string> = {
  "약국": "💊",
  "병·의원": "🏥",
  "응급실": "🚑",
  "산부인과": "🤰",
};
/** 병원·약국 표식에서 뺄 항목(화장실은 코스 쪽에서 보여 준다) */
const HELP_SKIP = new Set(["장애인 화장실", "기저귀 교환대"]);

/** 범례에 표시할 항목 정의 (kind, 한글 라벨, 색) — Python LEGEND 와 같은 순서 */
const LEGEND_DEF: [string, string, string][] = [
  ["place", "추천 장소(번호)", VERDICT_HEX["green"]],
  ["route", "코스", ROUTE_HEX],
  ["dot", "나들이 장소", DOT_HEX],
  ["caution", "조심할 곳", CAUTION_HEX],
  ["toilet", "장애인 화장실", TOILET_HEX],
  ["food", "식당", FOOD_HEX],
  ["help", "병원·약국", HELP_HEX],
];

// ── 공개 API ──────────────────────────────────────────────────────────────────

/**
 * 화면 상태(추천·식당·병원 등)를 받아 지도 표식 목록을 만든다.
 * Python map_view.build() 와 같은 로직.
 *
 * @param o.results   추천 장소 목록 (있으면 번호 표식, 없으면 allPlaces 점)
 * @param o.selected  현재 선택된 장소 이름 (big 표식 + fit)
 * @param o.detail    get_place_detail 결과 (all_points 포함 — 코스·화장실·위험 표식)
 * @param o.food      search_food 결과 (items 배열)
 * @param o.help      find_nearby_help 결과 (help 오브젝트)
 * @param o.allPlaces 나들이 장소 전체 — results 가 없을 때 초록 점으로 보여 준다
 */
export function buildMapData(o: {
  results?: any[];
  selected?: string | null;
  detail?: any;
  food?: any;
  help?: any;
  allPlaces?: PlaceDot[];
  /** 추천 장소 카드의 주소·사진을 찾을 나들이 장소 목록(점은 그리지 않는다) */
  placeInfo?: PlaceDot[];
  /** 휠체어 이용자인지(화장실 이름을 '장애인 화장실'로) */
  wheel?: boolean;
}): MapData {
  // 장소 카드에 보일 주소·사진(나들이 장소 목록에서 이름으로 찾는다)
  const info = new Map((o.placeInfo ?? o.allPlaces ?? []).map((p) => [p.place, p]));
  // 원자료 주소는 '제주 제주시 …'처럼 시·도가 겹쳐 있어 '제주시 …'로 줄인다
  const addr = (a?: string | null) => (a ? a.replace(/^제주(특별자치도)?\s+(?=(제주시|서귀포시))/, "") : a);
  const marks: MapMark[] = [];
  const route: [number, number][] = [];

  // ── 추천 장소 번호 표식 / 나들이 장소 점 ────────────────────────────────
  if (o.results && o.results.length > 0) {
    o.results.forEach((r, i) => {
      marks.push({
        kind: "place",
        lat: r.lat,
        lon: r.lon,
        text: String(i + 1),
        name: r.place,
        sub: r.verdict,
        address: addr(info.get(r.place)?.address) ?? r.where,
        photos: info.get(r.place)?.photos ?? [],
        color: VERDICT_HEX[r.verdict_color as string] ?? "#5F6B73",
        big: r.place === o.selected,
        pin: r.place === o.selected ? r.place : undefined,
        fit: r.place === o.selected || !o.selected,
      });
    });
  } else if (o.allPlaces != null) {
    o.allPlaces.forEach((r) => {
      marks.push({
        kind: "dot",
        lat: r.lat,
        lon: r.lon,
        name: r.place,
        sub: `${r.sigungu} ${r.dong}`,
        address: addr(r.address) ?? `${r.sigungu} ${r.dong}`,
        photos: r.photos ?? [],
        color: DOT_HEX,
      });
    });
  }

  // ── 코스 경로 + 위험·화장실 표식 ─────────────────────────────────────────
  if (o.detail?.all_points) {
    // '(=5)'처럼 앞 지점으로 되돌아온 기록은 선이 앞뒤로 튀므로 빼고, 혼자 툭 튀어나온 점도 선에서는 뺀다
    const pts = (o.detail.all_points as any[]).filter((p) => !/^\(=/.test(String(p.label ?? "")));
    route.push(...despike(pts.map((p) => [p.lat as number, p.lon as number] as [number, number])));
    for (const p of pts) {
      const flags = p.flags as string[];
      const caution = flags.filter((f) => !NOT_CAUTION.has(f));
      if (caution.length > 0) {
        marks.push({
          kind: "caution",
          lat: p.lat,
          lon: p.lon,
          text: "⚠️",
          name: `출발 후 약 ${p.at_m}m`,
          sub: caution.join(" · "),
          color: CAUTION_HEX,
        });
      } else if (flags.includes("장애인 화장실")) {
        marks.push({
          kind: "toilet",
          lat: p.lat,
          lon: p.lon,
          text: "🚻",
          name: o.wheel ? "장애인 화장실" : "넓은 화장실",
          sub: p.label as string,
          color: TOILET_HEX,
        });
      }
    }
  }

  // ── 식당 표식 ─────────────────────────────────────────────────────────────
  if (o.food) {
    const items: any[] = o.food.items ?? [];
    items.forEach((it, i) => {
      marks.push({
        kind: "food",
        big: i === 0,
        pin: i === 0 ? `추천 1 · ${it.name}` : undefined,
        lat: it.lat,
        lon: it.lon,
        text: "🍽️",
        name: it.name,
        sub:
          (it.food_type as string) +
          (it.wheelchair_entry ? (o.wheel ? " · 휠체어 진입 확인" : " · 입구 턱 없음") : ""),
        color: FOOD_HEX,
        ring: it.wheelchair_entry as boolean,
      });
    });
  }

  // ── 약국·병원 표식 ────────────────────────────────────────────────────────
  if (o.help) {
    const helpMap: Record<string, any[]> = o.help.help ?? {};
    for (const [kind, items] of Object.entries(helpMap)) {
      if (HELP_SKIP.has(kind)) continue;
      for (const it of items) {
        if (it.lat == null) continue;
        marks.push({
          kind: "help",
          lat: it.lat,
          lon: it.lon,
          text: HELP_SHORT[kind] ?? "🏥",
          name: it.name,
          sub: `${kind} · ${it.km}km`,
          color: HELP_HEX,
        });
      }
    }
  }

  return { marks, route, toiletLabel: o.wheel ? "장애인 화장실" : "넓은 화장실" };
}

/**
 * 현재 지도 데이터에 실제로 표시 중인 항목만 범례 아이템으로 돌려준다.
 * Python map_view.legend_items() 와 같은 로직.
 * @returns [[라벨, 색], ...] 쌍의 배열
 */
export function legendItems(d: MapData): [string, string][] {
  const kinds = new Set<string>(d.marks.map((m) => m.kind as string));
  if (d.route.length > 1) kinds.add("route"); // 점 하나는 선이 아니다(관광공사 장소는 입구 한 점뿐)
  const dots = d.marks.filter((m) => m.kind === "dot").length;
  return LEGEND_DEF.filter(([k]) => kinds.has(k)).map(([k, label, color]) => [
    k === "dot" ? `${label} ${dots}곳` : k === "toilet" ? (d.toiletLabel ?? label) : label,
    color,
  ]);
}

/** 코스 선에서 혼자 툭 튀어나왔다 돌아오는 점을 뺀다(앞뒤 점을 잇는 길보다 2.5배 넘게 돌아가면 뾰족한 가시) */
function despike(pts: [number, number][]): [number, number][] {
  if (pts.length < 3) return pts;
  const m = (a: [number, number], b: [number, number]) => {
    const dy = (a[0] - b[0]) * 110540;
    const dx = (a[1] - b[1]) * 111320 * Math.cos((a[0] * Math.PI) / 180);
    return Math.hypot(dx, dy);
  };
  const out: [number, number][] = [pts[0]];
  for (let i = 1; i < pts.length - 1; i++) {
    const a = out[out.length - 1], b = pts[i], c = pts[i + 1];
    const detour = m(a, b) + m(b, c), direct = m(a, c);
    if (detour > direct * 2.5 + 40) continue; // 가시처럼 튀어나온 점
    out.push(b);
  }
  out.push(pts[pts.length - 1]);
  return out;
}
