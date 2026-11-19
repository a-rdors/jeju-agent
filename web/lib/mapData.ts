/**
 * mapData.ts — buildMapData() / legendItems() 순수 함수.
 * Python app/map_view.py 의 build() 와 legend_items() 를 그대로 옮긴 것이다.
 * React 에 의존하지 않으며 서버와 클라이언트 모두에서 사용할 수 있다.
 */
/* eslint-disable @typescript-eslint/no-explicit-any */
import type { MapData, MapMark, PlaceDot } from "./types";
import { FILL } from "./icons";

// ── 색 상수: app/globals.css 의 토큰과 같은 값(web/DESIGN.md) ─────────────────
// 지도 표식은 카카오 지도 위에 JS 로 그리므로 CSS 변수 대신 같은 값을 여기 둔다.
export const VERDICT_HEX: Record<string, string> = {
  green: "#2F7A4D",
  orange: "#2C6EA6",
  gray: "#5E6368", // --slate
};

export const CAUTION_HEX = "#B83227"; // --red
// 색은 종류마다 다르게: 추천 장소=판정색(초록·주황·회색), 코스=파랑, 화장실=청록, 조심할 곳=빨강
export const ROUTE_HEX = "#2F6FD6"; // --map-route
export const DOT_HEX = "#2F7A4D"; // --leaf
export const DOT_GYUL_HEX = "#F0892B"; // --gyul (지역 구분용 두 번째 점 색)
export const TOILET_HEX = "#0E8A8A"; // --map-toilet
export const FOOD_HEX = "#E07A1C"; // --map-food
export const HELP_HEX = "#5B3A8C"; // --map-help

/** 지도 위험 표시에서 제외할 접근성 항목 (화장실·주차는 경고가 아니라 정보) */
export const NOT_CAUTION: Set<string> = new Set(["장애인 화장실", "장애인 주차", "넓은 화장실", "주차장"]);

// ── 내부 상수 ─────────────────────────────────────────────────────────────────
// 지도 표식 그림(이모지 대신 흰 그림). 약국만 따로, 나머지 병원은 십자 그림
const HELP_ICON: Record<string, string> = {
  "약국": FILL.local_pharmacy,
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
  /** 지금 고른 가게·병원(하르방이 추천했거나 사용자가 누른 곳). 이 표식만 크게 + 이름표 */
  focus?: string | null;
}): MapData {
  const shopNames = [
    ...((o.food?.items ?? []) as any[]).map((it) => it.name),
    ...Object.values((o.help?.help ?? {}) as Record<string, any[]>).flat().map((it) => it.name),
  ];
  const pickedShop = !!o.focus && shopNames.includes(o.focus);
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
        // 이름표는 한 번에 하나: 식당·병원을 고른 동안은 장소 이름표를 숨긴다
        pin: r.place === o.selected && !pickedShop ? r.place : undefined,
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
        area: areaOf(r.sigungu, r.dong),
        color: regionHex(areaOf(r.sigungu, r.dong)),
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
          text: "!",
          name: `출발 후 약 ${p.at_m}m`,
          sub: caution.join(" · "),
          color: CAUTION_HEX,
        });
      } else if (flags.includes("장애인 화장실")) {
        marks.push({
          kind: "toilet",
          lat: p.lat,
          lon: p.lon,
          icon: FILL.wc,
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
    items.forEach((it) => {
      marks.push({
        kind: "food",
        big: !!o.focus && it.name === o.focus,
        pin: o.focus && it.name === o.focus ? it.name : undefined,
        lat: it.lat,
        lon: it.lon,
        icon: FILL.restaurant,
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
          big: !!o.focus && it.name === o.focus,
          pin: o.focus && it.name === o.focus ? it.name : undefined,
          lat: it.lat,
          lon: it.lon,
          icon: HELP_ICON[kind] ?? FILL.local_hospital,
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

/** 중문 관광단지 언저리의 서귀포시 동(시내가 아니라 '중문'으로 부른다) */
const JUNGMUN = new Set(["중문동", "색달동", "대포동", "예래동", "상예동", "하예동", "하원동", "회수동", "도순동"]);

/**
 * 지도 지역: 제주관광공사 비짓제주(visitjeju.net)의 관광지 지역 구분을 따른다.
 * 제주시 = 제주시내·애월·한림·한경·조천·구좌·우도·추자, 서귀포시 = 서귀포시내·중문·안덕·대정·남원·표선·성산.
 * 색은 섬 둘레를 따라 이웃 지역끼리 초록·감귤이 번갈아 오도록 정했다.
 * 둘레의 지역이 13곳(홀수)이라 한 쌍은 같은 색이 되는데, 이웃 중 점이 가장 멀리 떨어진 표선·남원(약 7km)으로 했다.
 */
export const REGION_TONE: Record<string, "leaf" | "gyul"> = {
  제주시내: "leaf", 조천: "gyul", 구좌: "leaf", 우도: "gyul", 성산: "gyul", 표선: "leaf", 남원: "leaf",
  서귀포시내: "gyul", 중문: "leaf", 안덕: "gyul", 대정: "leaf", 한경: "gyul", 한림: "leaf", 애월: "gyul", 추자: "gyul",
};

/**
 * 섬 전체를 볼 때 지역 이름표를 놓을 자리(위도, 경도). 관광안내도처럼 이름표끼리 겹치지 않게 손으로 정했다.
 * 남쪽 해안의 대정·중문·서귀포시내는 바다 쪽으로, 안덕은 안쪽으로 엇갈리게 두어 휴대폰 화면에서도 겹치지 않는다.
 * 없는 지역은 그 지역 장소들의 가운데에 둔다.
 */
export const REGION_ANCHOR: Record<string, [number, number]> = {
  제주시내: [33.52, 126.5], 조천: [33.47, 126.65], 구좌: [33.53, 126.8], 우도: [33.51, 126.96],
  성산: [33.43, 126.9], 표선: [33.36, 126.83], 남원: [33.28, 126.7], 서귀포시내: [33.22, 126.6],
  중문: [33.215, 126.42], 안덕: [33.3, 126.36], 대정: [33.2, 126.24], 한경: [33.31, 126.18],
  한림: [33.39, 126.24], 애월: [33.46, 126.36],
};

/** 지역의 점 색(초록 또는 감귤). 모르는 지역은 초록 */
export function regionHex(area?: string | null): string {
  return REGION_TONE[area ?? ""] === "gyul" ? DOT_GYUL_HEX : DOT_HEX;
}

/**
 * 장소의 지역 이름(비짓제주 지역 구분). 읍·면은 '애월', '성산'처럼 끝 글자를 떼고,
 * 시내의 잘게 나뉜 동은 '제주시내'·'서귀포시내'·'중문'으로 묶는다.
 */
export function areaOf(sigungu?: string | null, dong?: string | null): string {
  const d = (dong ?? "").trim();
  if (/[읍면]$/.test(d) && d.length > 1) return d.slice(0, -1);
  if (JUNGMUN.has(d)) return "중문";
  if (sigungu === "서귀포시") return "서귀포시내";
  if (sigungu === "제주시") return "제주시내";
  return d || sigungu || "";
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
