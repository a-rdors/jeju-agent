"use client";
// 주소(GET URL)를 열쇠로 결과를 저장해 두고 다시 쓴다(main.py 의 st.cache_data 와 같은 역할).
// 날씨는 15분이 지나면 다시 불러온다.
import { useEffect, useSyncExternalStore } from "react";
import { getJSON } from "./api";

export interface Entry<T> {
  data?: T;
  error?: unknown;
  loading: boolean;
  at: number;
}

const TTL: [string, number][] = [["/api/weather", 15 * 60 * 1000]];
const cache = new Map<string, Entry<unknown>>();
const listeners = new Set<() => void>();

function emit() {
  listeners.forEach((l) => l());
}

function subscribe(l: () => void) {
  listeners.add(l);
  return () => {
    listeners.delete(l);
  };
}

function stale(url: string, e: Entry<unknown>) {
  if (e.error) return true; // 실패했으면 다음에 다시 시도
  const ttl = TTL.find(([p]) => url.startsWith(p))?.[1];
  return ttl !== undefined && !e.loading && Date.now() - e.at > ttl;
}

/** 아직 없거나 오래된 결과면 불러온다. 같은 주소를 여러 곳에서 불러도 한 번만 요청한다. */
export function load(url: string) {
  const hit = cache.get(url);
  if (hit && !stale(url, hit)) return;
  cache.set(url, { ...hit, loading: true, at: Date.now() });
  emit();
  getJSON<unknown>(url).then(
    (data) => cache.set(url, { data, loading: false, at: Date.now() }),
    (error) => cache.set(url, { error, loading: false, at: Date.now() }),
  ).finally(emit);
}

/** useApi(주소) -> {data, error, loading}. 주소가 null 이면 아무것도 안 한다. */
export function useApi<T>(url: string | null): Entry<T> {
  const entry = useSyncExternalStore(
    subscribe,
    () => (url ? cache.get(url) : undefined),
    () => undefined,
  ) as Entry<T> | undefined;
  useEffect(() => {
    if (url) load(url);
  }, [url]);
  return entry ?? { loading: url !== null, at: 0 };
}
