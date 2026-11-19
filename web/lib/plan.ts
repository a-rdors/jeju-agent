// '내 일정': 담은 장소·식당 목록. 로그인 없이 이 브라우저(localStorage)에 저장한다.
// 다른 기기·시크릿 창·사이트 데이터 지우기에서는 남지 않으므로, 일정표 내려받기로 파일을 갖고 있게 한다.
import { useSyncExternalStore } from "react";
import type { FoodItem } from "./api";

export interface PlanPlace {
  kind: "place";
  name: string;
  where?: string;
  lat: number;
  lon: number;
  verdict?: string;
  verdict_color?: string;
}

export interface PlanFood extends Omit<FoodItem, "km" | "open_status"> {
  kind: "food";
}

export type PlanItem = PlanPlace | PlanFood;

/** 한 장짜리 일정표에 담을 만큼(서버도 10곳까지만 쓴다) */
export const PLAN_MAX = 10;
const KEY = "jeju-plan-v1";

const EMPTY: PlanItem[] = [];
let items: PlanItem[] = EMPTY;
let loaded = false;
const listeners = new Set<() => void>();

function valid(x: unknown): x is PlanItem {
  if (typeof x !== "object" || x === null) return false;
  const o = x as Record<string, unknown>;
  return (o.kind === "place" || o.kind === "food") && typeof o.name === "string"
    && typeof o.lat === "number" && typeof o.lon === "number";
}

function load() {
  if (loaded || typeof window === "undefined") return;
  loaded = true;
  try {
    const raw = JSON.parse(window.localStorage.getItem(KEY) ?? "[]");
    if (Array.isArray(raw)) items = raw.filter(valid).slice(0, PLAN_MAX);
  } catch {
    // 저장소를 못 쓰는 브라우저(시크릿 창 등): 이번 방문 동안만 기억한다
  }
}

function save(next: PlanItem[]) {
  items = next;
  try {
    window.localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    // 저장 실패해도 화면 목록은 그대로 쓴다
  }
  listeners.forEach((l) => l());
}

export function getPlan(): PlanItem[] {
  load();
  return items;
}

export function usePlan(): PlanItem[] {
  return useSyncExternalStore(
    (l) => {
      listeners.add(l);
      // 다른 탭에서 담거나 뺀 것도 따라온다
      const onStorage = (e: StorageEvent) => {
        if (e.key !== KEY) return;
        loaded = false;
        load();
        l();
      };
      window.addEventListener("storage", onStorage);
      return () => {
        listeners.delete(l);
        window.removeEventListener("storage", onStorage);
      };
    },
    getPlan,
    () => EMPTY,
  );
}

export function inPlan(list: PlanItem[], name: string): boolean {
  return list.some((it) => it.name === name);
}

/** 담기. 이미 있으면 그대로, 가득 차면 false */
export function addToPlan(it: PlanItem): boolean {
  const cur = getPlan();
  if (inPlan(cur, it.name)) return true;
  if (cur.length >= PLAN_MAX) return false;
  save([...cur, it]);
  return true;
}

export function removeFromPlan(name: string) {
  save(getPlan().filter((it) => it.name !== name));
}

/** i 번째를 d(-1 위, +1 아래)만큼 옮긴다 */
export function movePlan(i: number, d: number) {
  const cur = [...getPlan()];
  const j = i + d;
  if (i < 0 || j < 0 || i >= cur.length || j >= cur.length) return;
  [cur[i], cur[j]] = [cur[j], cur[i]];
  save(cur);
}

export function clearPlan() {
  save([]);
}

/** 두 곳 사이 직선거리(km, 소수 한 자리) */
export function kmBetween(a: { lat: number; lon: number }, b: { lat: number; lon: number }): number {
  const r = 6371;
  const dLat = ((b.lat - a.lat) * Math.PI) / 180;
  const dLon = ((b.lon - a.lon) * Math.PI) / 180;
  const h = Math.sin(dLat / 2) ** 2
    + Math.cos((a.lat * Math.PI) / 180) * Math.cos((b.lat * Math.PI) / 180) * Math.sin(dLon / 2) ** 2;
  return Math.round(2 * r * Math.asin(Math.sqrt(h)) * 10) / 10;
}
