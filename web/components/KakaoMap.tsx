/**
 * KakaoMap — 제주 나들이 지도 컴포넌트 (카카오맵 JavaScript SDK)
 *
 * 사전 준비 (카카오 개발자 콘솔 설정 필수):
 *   1. https://developers.kakao.com → 내 애플리케이션 선택
 *   2. 앱 설정 → 플랫폼 → Web 플랫폼 추가 → 사이트 도메인에 http://localhost:3000 등록
 *   3. 카카오맵 API 사용 설정 ON
 *   4. JavaScript 키를 props.kakaoKey 로 전달 (예: NEXT_PUBLIC_KAKAO_JS_KEY)
 *
 * @module KakaoMap
 */
"use client";
/* eslint-disable @typescript-eslint/no-explicit-any */

import "./KakaoMap.module.css";
import { useRef, useEffect, useLayoutEffect } from "react";
import type { MapData } from "../lib/types";

// ── Kakao Maps SDK 전역 타입 선언 ─────────────────────────────────────────────
declare global {
  interface Window {
    /** SDK 로드 Promise (전역 단일 인스턴스) */
    __jejuKakao?: Promise<void> | null;
    /** 카카오맵 SDK 전역 객체 */
    kakao?: { maps: any };
  }
}

// ── 내부 타입 ─────────────────────────────────────────────────────────────────
interface MapState {
  map: any;
  layers: any[];
  open: any;
  jeju: any;
  bounds: any;
  sig: string;
  psig: string;
}

/** 현재 렌더 사이클의 최신 props (비동기 콜백용) */
interface LatestProps {
  data: MapData;
  panelOpen: boolean;
  chatOpen: boolean;
}

// ── 상수 ─────────────────────────────────────────────────────────────────────
/** 마커 z-index 순서 (Python ORDER 와 동일) */
const ORDER: Record<string, number> = {
  dot: 1,
  toilet: 2,
  caution: 3,
  help: 4,
  food: 5,
  place: 6,
};

/** 제주도 위경도 경계 — 지도 중심이 이 밖으로 나가지 못한다 */
const JEJU = { s: 33.05, n: 33.66, w: 126.05, e: 127.08 };

// ── 헬퍼 함수 ─────────────────────────────────────────────────────────────────

/** HTML 특수 문자 이스케이프 */
function esc(t: unknown): string {
  return String(t ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ] ?? c,
  );
}

/** 현재 뷰포트가 모바일(640px 미만)인지 확인 */
function small(): boolean {
  return window.innerWidth < 640;
}

/**
 * 지도 위에 떠 있는 UI 요소(상단 바·대시보드·대화창·하단 시트)를 피하는 여백을 계산한다.
 * [위, 오른쪽, 아래, 왼쪽] 순서 — Python pads() 와 동일 로직.
 */
function pads(
  panelOpen: boolean,
  chatOpen: boolean,
): [number, number, number, number] {
  const w = window.innerWidth,
    h = window.innerHeight;
  // 휴대폰: 위쪽 상자+범례(약 110px), 아래쪽 시트(화면의 46%)
  if (small()) return [116, 28, panelOpen ? Math.round(h * 0.46) + 28 : 40, 28];
  // 넓은 화면: 대화창은 대시보드 자리에 겹쳐 뜨므로 오른쪽은 둘 중 하나만 열려도 같은 폭(420+16)을 비운다.
  // 왼쪽은 이름표·설정 상자와 범례(약 170px) 자리.
  const r = 40 + (panelOpen || chatOpen ? 436 : 0);
  return [40, Math.min(r, w - 280), 40, 190];
}

/**
 * 카카오맵 SDK 를 한 번만 로드한다.
 * 이미 로드 중이거나 완료된 경우 기존 Promise 를 재사용한다.
 */
function loadSdk(key: string): Promise<void> {
  if (window.kakao && window.kakao.maps && window.kakao.maps.Map) {
    return Promise.resolve();
  }
  if (!window.__jejuKakao) {
    window.__jejuKakao = new Promise<void>((ok, bad) => {
      const s = document.createElement("script");
      s.src =
        "https://dapi.kakao.com/v2/maps/sdk.js?autoload=false&appkey=" +
        encodeURIComponent(key);
      s.onerror = () => bad(new Error("Kakao Maps SDK 로드 실패"));
      s.onload = () => {
        if (window.kakao && window.kakao.maps) {
          window.kakao.maps.load(ok);
        } else {
          bad(new Error("kakao.maps 를 찾을 수 없음"));
        }
      };
      document.head.appendChild(s);
    }).catch((e) => {
      window.__jejuKakao = null;
      throw e;
    });
  }
  return window.__jejuKakao as Promise<void>;
}

/** 열려 있는 툴팁을 닫는다 */
function closeTip(state: MapState): void {
  if (state.open) {
    state.open.setMap(null);
    state.open = null;
  }
}

/** 열린 말풍선이 상단 상자·패널·화면 끝에 가리면 그만큼 지도를 민다 */
function reveal(state: MapState, el: HTMLElement): void {
  requestAnimationFrame(() => {
    const r = el.getBoundingClientRect();
    if (!r.width) return;
    const [t, pr, pb, pl] = JSON.parse(state.psig || "[40,40,40,40]") as number[];
    const W = window.innerWidth, H = window.innerHeight, g = 12;
    let dx = 0, dy = 0;
    if (r.right > W - pr + 20) dx = r.right - (W - pr + 20) + g;
    else if (r.left < pl - 60) dx = r.left - (pl - 60) - g;
    if (r.top < t) dy = r.top - t - g;
    else if (r.bottom > H - pb) dy = r.bottom - (H - pb) + g;
    if (dx || dy) state.map.panBy(Math.round(dx), Math.round(dy));
  });
}

/** 지도를 현재 여백에 맞춰 다시 맞춘다 */
function fitMap(
  state: MapState,
  panelOpen: boolean,
  chatOpen: boolean,
): void {
  state.map.relayout();
  const [t, r, b, l] = pads(panelOpen, chatOpen);
  state.map.setBounds(state.bounds || state.jeju, t, r, b, l);
}

/**
 * 마커·경로·범례를 그린다. Python draw() 와 같은 로직.
 * 표식이 바뀌지 않았으면 사용자가 이동한 화면을 그대로 유지하고,
 * 여백만 바뀌었으면 re-fit 만 수행한다.
 */
function drawMarkers(
  root: HTMLElement,
  state: MapState,
  data: MapData,
  panelOpen: boolean,
  chatOpen: boolean,
  onPickRef: React.RefObject<(name: string) => void>,
  onLookRef: React.RefObject<(name: string) => void>,
): void {
  const k = window.kakao!.maps;
  const sig = JSON.stringify([data.marks, data.route]);
  const p = pads(panelOpen, chatOpen);
  const psig = JSON.stringify(p);

  // 표식이 같으면 사용자가 이동한 화면을 유지한다
  if (sig === state.sig) {
    if (psig !== state.psig) {
      // 패널·대화창을 열고 닫은 것뿐이면 확대 단계는 그대로 두고 보이는 가운데만 옆으로 민다.
      // (setBounds 로 다시 맞추면 확대 단계가 바뀌어 지도 조각을 새로 불러오며 화면이 깜빡인다)
      const [ot, or, ob, ol] = JSON.parse(state.psig || psig) as number[];
      const [t, r, b, l] = p;
      const dx = Math.round(((r - l) - (or - ol)) / 2);
      const dy = Math.round(((b - t) - (ob - ot)) / 2);
      state.psig = psig;
      if (dx || dy) state.map.panBy(dx, dy);
    }
    return;
  }

  state.sig = sig;
  state.psig = psig;
  closeTip(state);
  state.layers.forEach((o) => o.setMap(null));
  state.layers = [];

  const b = new k.LatLngBounds();
  let n = 0;

  // 코스 경로
  if (data.route.length > 1) {
    const path = data.route.map((p) => new k.LatLng(p[0], p[1]));
    state.layers.push(
      new k.Polyline({
        map: state.map,
        path,
        strokeWeight: 6,
        strokeColor: "#2F7A4D",
        strokeOpacity: 0.85,
      }),
    );
    path.forEach((p) => {
      b.extend(p);
      n++;
    });
  }

  // 마커
  data.marks.forEach((m) => {
    const pos = new k.LatLng(m.lat, m.lon);
    if (m.fit !== false && m.kind !== "dot") {
      b.extend(pos);
      n++;
    }

    // 마커 DOM 요소
    const el = document.createElement("div");
    el.className =
      `km-mk ${m.kind}` +
      (m.big ? " big" : "") +
      (m.ring ? " ring" : "");
    el.style.background = m.color;
    el.textContent = m.text || "";
    el.tabIndex = 0;
    el.setAttribute("role", "button");
    el.setAttribute("aria-label", `${m.name}, ${m.sub || ""}`);

    const overlay = new k.CustomOverlay({
      map: state.map,
      position: pos,
      content: el,
      yAnchor: 0.5,
      zIndex: ORDER[m.kind] + (m.big ? 10 : 0),
    });
    state.layers.push(overlay);

    // 누르면 뜨는 말풍선. 나들이·추천 장소는 '장소 카드'(사진·이름·주소 + 자세히 살펴보기),
    // 식당·병원·확인할 지점 등은 짧은 설명.
    const route = `https://map.kakao.com/link/to/${encodeURIComponent(m.name)},${m.lat},${m.lon}`;
    const tip = document.createElement("div");
    if (m.kind === "place" || m.kind === "dot") {
      const photos = (m.photos ?? []).slice(0, 3);
      tip.className = "km-card" + (photos.length ? "" : " no-ph");
      tip.setAttribute("role", "dialog");
      tip.setAttribute("aria-label", `${m.name} 간단 정보`);
      const ph = photos.length
        ? `<div class="km-ph n${photos.length}">` +
          photos.map((u) => `<img src="${esc(u)}" alt="" loading="lazy">`).join("") +
          "</div>"
        : "";
      const badge = m.kind === "place"
        ? `<span class="km-badge" style="background:${esc(m.color)}">${esc(m.text)}번 · ${esc(m.sub)}</span>`
        : "";
      tip.innerHTML =
        '<button type="button" class="km-x" aria-label="닫기">×</button>' + ph +
        `<div class="km-body">${badge}<b>${esc(m.name)}</b><small>${esc(m.address || m.sub)}</small>` +
        (photos.length ? '<span class="km-cr">사진: 제주데이터허브 무장애여행 정보</span>' : "") +
        '<div class="km-acts"><button type="button" class="km-more">자세히 살펴보기</button>' +
        `<a class="km-go" href="${route}" target="_blank" rel="noopener">길안내</a></div></div>`;
      tip.querySelectorAll("img").forEach((img) => img.addEventListener("error", () => img.remove()));
      tip.querySelector(".km-x")?.addEventListener("click", (e) => {
        e.stopPropagation();
        closeTip(state);
        el.focus();
      });
      tip.querySelector(".km-more")?.addEventListener("click", (e) => {
        e.stopPropagation();
        closeTip(state);
        // 추천 장소는 그 결과(한눈에)로, 나들이 장소는 코스 정보를 패널에 띄운다
        (m.kind === "place" ? onPickRef : onLookRef).current?.(m.name);
      });
    } else {
      tip.className = "km-tip";
      const act = m.kind === "food" || m.kind === "help"
        ? `<br><a href="${route}" target="_blank" rel="noopener">길안내 열기</a>` : "";
      tip.innerHTML = `<b>${esc(m.name)}</b><small>${esc(m.sub)}</small>${act}`;
    }
    // 말풍선 안을 누르거나 끌어도 지도가 따라 움직이거나 닫히지 않게
    for (const ev of ["mousedown", "touchstart", "click", "dblclick"]) {
      tip.addEventListener(ev, (e) => e.stopPropagation());
    }

    const info = new k.CustomOverlay({
      position: pos,
      content: tip,
      yAnchor: 1,
      zIndex: 50,
    });

    // 마커 클릭/키보드 동작: 말풍선을 열고 닫는다(열면 화면 안에 들어오게 지도를 조금 민다)
    const act2 = () => {
      const same = state.open === info;
      closeTip(state);
      if (!same) {
        info.setMap(state.map);
        state.open = info;
        reveal(state, tip);
      }
    };

    el.addEventListener("click", (e) => {
      e.stopPropagation();
      act2();
    });
    el.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        act2();
      }
    });
  });

  // 경계가 너무 좁으면 살짝 넓혀 한 점만 있을 때 너무 확대되지 않게 한다
  if (n > 0) {
    const sw = b.getSouthWest(),
      ne = b.getNorthEast(),
      d = 0.004;
    if (ne.getLat() - sw.getLat() < 2 * d) {
      b.extend(new k.LatLng(sw.getLat() - d, sw.getLng()));
      b.extend(new k.LatLng(ne.getLat() + d, ne.getLng()));
    }
    if (ne.getLng() - sw.getLng() < 2 * d) {
      b.extend(new k.LatLng(sw.getLat(), sw.getLng() - d));
      b.extend(new k.LatLng(ne.getLat(), ne.getLng() + d));
    }
  }

  state.bounds = n > 0 ? b : null;
  fitMap(state, panelOpen, chatOpen);
}

// ── KakaoMap 컴포넌트 ─────────────────────────────────────────────────────────

export default function KakaoMap({
  kakaoKey,
  data,
  panelOpen,
  chatOpen,
  onPick,
  onLook,
}: {
  kakaoKey: string;
  data: MapData;
  panelOpen: boolean;
  chatOpen: boolean;
  onPick: (name: string) => void;
  onLook: (name: string) => void;
}) {
  const rootRef = useRef<HTMLDivElement>(null);
  const stateRef = useRef<MapState | null>(null);

  // 콜백을 ref 에 보관해 핸들러 identity 가 바뀌어도 맵을 다시 만들지 않는다
  const onPickRef = useRef(onPick);
  const onLookRef = useRef(onLook);

  // 비동기 SDK 콜백에서 항상 최신 props 를 읽기 위한 ref
  const latestRef = useRef<LatestProps>({ data, panelOpen, chatOpen });

  // useLayoutEffect 로 콜백·최신 props ref 를 동기 갱신한다
  // (render 단계에서 ref.current 를 직접 쓰면 react-hooks/refs 규칙에 위반된다)
  useLayoutEffect(() => {
    onPickRef.current = onPick;
    onLookRef.current = onLook;
    latestRef.current = { data, panelOpen, chatOpen };
  });

  // ── SDK 로드 + 지도 초기화 (kakaoKey 가 바뀔 때만) ──────────────────────
  useEffect(() => {
    if (!kakaoKey || !rootRef.current) return;

    const root = rootRef.current;
    let resizeTimer: ReturnType<typeof setTimeout>;

    const handleResize = () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        if (stateRef.current) {
          fitMap(
            stateRef.current,
            latestRef.current.panelOpen,
            latestRef.current.chatOpen,
          );
        }
      }, 200);
    };

    window.addEventListener("resize", handleResize);

    loadSdk(kakaoKey)
      .then(() => {
        if (!rootRef.current) return; // 언마운트된 경우

        // 지도는 한 번만 초기화
        if (!stateRef.current) {
          const k = window.kakao!.maps;
          const mapEl = root.querySelector(".km-map") as HTMLElement;
          const map = new k.Map(mapEl, {
            center: new k.LatLng(33.38, 126.55),
            level: small() ? 11 : 10,
          });
          map.setMaxLevel(small() ? 11 : 10); // 너무 멀리 줄여 육지까지 보이지 않게


          const state: MapState = {
            map,
            layers: [],
            open: null,
            jeju: new k.LatLngBounds(
              new k.LatLng(33.19, 126.15),
              new k.LatLng(33.57, 126.97),
            ),
            bounds: null,
            sig: "",
            psig: "",
          };
          stateRef.current = state;

          // 제주도 밖으로 중심이 나가지 않도록 클램프
          const clamp = () => {
            const c = map.getCenter();
            const lat = Math.min(JEJU.n, Math.max(JEJU.s, c.getLat()));
            const lng = Math.min(JEJU.e, Math.max(JEJU.w, c.getLng()));
            if (lat !== c.getLat() || lng !== c.getLng()) {
              map.panTo(new k.LatLng(lat, lng));
            }
          };
          k.event.addListener(map, "dragend", clamp);
          k.event.addListener(map, "zoom_changed", clamp);
          k.event.addListener(map, "click", () => closeTip(state));
        }

        // 최신 props 로 초기 렌더
        const { data: d, panelOpen: po, chatOpen: co } = latestRef.current;
        drawMarkers(root, stateRef.current!, d, po, co, onPickRef, onLookRef);
      })
      .catch(() => {
        // SDK 로드 실패 → 에러 메시지 표시
        const errEl = root.querySelector(".km-err") as HTMLElement | null;
        if (errEl) errEl.style.display = "flex";
      });

    return () => {
      window.removeEventListener("resize", handleResize);
      clearTimeout(resizeTimer);
    };
  }, [kakaoKey]);

  // ── 데이터·패널·채팅 상태 변경 시 마커만 다시 그린다 ─────────────────────
  useEffect(() => {
    if (!stateRef.current || !rootRef.current) return;
    drawMarkers(
      rootRef.current,
      stateRef.current,
      data,
      panelOpen,
      chatOpen,
      onPickRef,
      onLookRef,
    );
  }, [data, panelOpen, chatOpen]);

  // 확대·축소(넓은 화면). 카카오 기본 버튼은 축척과 겹쳐서 축척 위쪽에 따로 둔다.
  const zoom = (d: number) => {
    const map = stateRef.current?.map;
    if (!map) return;
    const next = map.getLevel() + d;
    if (next < 1 || next > (small() ? 11 : 10)) return;
    map.setLevel(next, { animate: { duration: 220 } });
  };

  return (
    <div className="km-root" ref={rootRef}>
      <div
        className="km-map"
        role="application"
        aria-label="제주 나들이 지도"
      />
      {kakaoKey && (
        <div className="km-zoom" role="group" aria-label="지도 확대·축소">
          <button type="button" onClick={() => zoom(-1)} aria-label="지도 확대" title="확대">+</button>
          <button type="button" onClick={() => zoom(1)} aria-label="지도 축소" title="축소">−</button>
        </div>
      )}
      {/* 키가 비어 있거나 SDK 로드 실패 시 보이는 에러 안내 */}
      <div
        className="km-err"
        style={!kakaoKey ? { display: "flex" } : undefined}
      >
        카카오맵을 불러오지 못했어요.
        <br />
        KAKAO_JS_KEY와 등록한 사이트 주소를 확인해 주세요.
      </div>
    </div>
  );
}
