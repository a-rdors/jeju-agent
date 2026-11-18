"use client";
// 오른쪽 대시보드(휴대폰은 아래 시트). 시작 / 결과(한눈에·코스·식당·병원·약국) / 식당 / 장소·병원 답.
import { useEffect, useRef, type KeyboardEvent, type PointerEvent } from "react";
import { NOT_CAUTION, VERDICT_HEX } from "@/lib/mapData";
import { ART, ICON, dataUri } from "@/lib/art";
import { USER_TYPES, isError, kakaoRouteLink, urls } from "@/lib/api";
import type { BusStop, Detail, Food, Help, Nearby, PlaceResult, Weather } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import {
  TABS, conditionTexts, focusItem, go, pick, setSheet, setTab, toResult, togglePanel, topPlace,
  type State, type Tab,
} from "@/lib/store";
import {
  Caption, Checks, Info, LinkButton, Loading, Notes, PlaceHead, Sect, Shop, Src, Svg, Tiles, Timeline,
  Verdict, WeatherBox,
} from "./bits";
import { VerdictWithEvidence } from "./Evidence";
import Icon from "./Icon";

// (버튼 글자, 아이콘, 이동 유형, 보낼 문장, 설명, 아이콘 배경)
const TYPES: [string, string, string, string, string, string][] = [
  ["휠체어와 함께", "wheel", "manual_wheelchair", "휠체어 타는 가족과 나들이 갈 곳 추천해 줘", "경사·턱·장애인 화장실을 먼저 봐요", "#E3F1E7"],
  ["유모차와 함께", "stroller", "stroller", "유모차 끌고 갈 만한 곳 추천해 줘", "계단 없는 길, 쉬어 갈 곳을 봐요", "#FDE9D6"],
  ["어르신과 함께", "senior", "senior", "부모님 모시고 가볍게 다녀올 곳 추천해 줘", "짧고 완만한 길, 앉을 곳을 봐요", "#E2EDF7"],
];

const fmt = (n: number) => n.toLocaleString("ko-KR");

// ---------- 공통 조각 ----------
/** 지도 표식·대화 단추와 함께 움직이는 카드: 고른 곳이면 강조하고 보이게 내린다 */
function FocusCard({ name, focus, children }: { name: string; focus?: string | null; children: React.ReactNode }) {
  const ref = useRef<HTMLLIElement>(null);
  const on = !!focus && focus === name;
  useEffect(() => {
    if (on) ref.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [on]);
  return <li ref={ref} className={`card${on ? " focus" : ""}`}>{children}</li>;
}

function MapButton({ name }: { name: string }) {
  return (
    <button type="button" className="btn btn-secondary" onClick={() => focusItem(name)} aria-label={`${name} 지도에서 보기`}>
      <Icon name="map" /><span>지도</span>
    </button>
  );
}

function ShopCard({ it, focus }: { it: Food["items"][number]; focus?: string | null }) {
  const tags: [string, string][] = it.wheelchair_entry ? [["휠체어 진입 확인(2021)", "wc"]] : [];
  tags.push(...(it.why ?? []).map((w): [string, string] => [w.split(":")[0] + " (추정)", ""]));
  const meta = it.food_type + (it.km !== null && it.km !== undefined ? ` · ${it.km}km` : "");
  return (
    <FocusCard name={it.name} focus={focus}>
      <Shop name={it.name} meta={meta} tags={tags} />
      <div className="row">
        <LinkButton href={kakaoRouteLink(it.name, it.lat, it.lon)} icon="directions" kind="primary">길안내</LinkButton>
        {it.phone && <LinkButton href={`tel:${it.phone}`} icon="call">전화 {it.phone}</LinkButton>}
        <MapButton name={it.name} />
      </div>
    </FocusCard>
  );
}

function FoodList({ f, focus }: { f: Food; focus?: string | null }) {
  if (f.anchor_not_found) return <Info>{f.note}</Info>;
  return (
    <>
      {!f.items.length && <Info>조건에 맞는 식당을 찾지 못했어요. 조건을 줄이거나 동네를 바꿔 말해 보세요.</Info>}
      {f.items.length > 0 && (
        <ul className="cards">
          {f.items.map((it, i) => <ShopCard key={`${it.name}-${i}`} it={it} focus={focus} />)}
        </ul>
      )}
      <Src>{f.note}</Src>
    </>
  );
}

/** 병원·약국 탭에는 병원·약국·응급실만(화장실은 코스 탭에서 보여 준다) */
const HELP_ONLY = new Set(["응급실", "병·의원", "약국", "산부인과"]);

function HelpList({ h, focus }: { h: Help; focus?: string | null }) {
  if (isError(h)) return <Caption>{h.error}</Caption>;
  return (
    <>
      <ul className="cards">
        {Object.entries(h.help ?? {}).filter(([kind]) => HELP_ONLY.has(kind)).flatMap(([kind, items]) =>
          items.map((it, i) => (
            <FocusCard key={`${kind}-${i}`} name={it.name} focus={focus}>
              <Shop name={it.name} meta={[kind, it.km !== null && it.km !== undefined ? `${it.km}km` : "", it.address].filter(Boolean).join(" · ")}
                tags={it.status ? [[it.status, "wc"]] : []} />
              <div className="row">
                <LinkButton href={kakaoRouteLink(it.name, it.lat, it.lon)} icon="directions" kind="primary">길안내</LinkButton>
                {it.phone && <LinkButton href={`tel:${it.phone}`} icon="call">전화 {it.phone}</LinkButton>}
                <MapButton name={it.name} />
              </div>
            </FocusCard>
          )),
        )}
      </ul>
      <Src>거리는 직선거리예요. 급할 때는 119에 먼저 전화하세요. 전화번호는 카카오 장소 정보로 찾았어요.</Src>
    </>
  );
}

/** 개요 카드의 한 줄: 출발점에서 가까운 정류소 */
function BusLine({ stops }: { stops?: BusStop[] }) {
  if (!stops?.length) return null;
  return (
    <div className="busline">
      <Icon name="bus" />
      <span><b>가까운 정류소</b> {stops.map((b) => `${b.name} ${fmt(b.m)}m`).join(" · ")}</span>
    </div>
  );
}

function BackButton({ s }: { s: State }) {
  const top = topPlace(s);
  if (!top) return null;
  return (
    <button type="button" className="btn btn-tertiary back" onClick={toResult}>
      <Icon name="arrow_back" />
      <span>{s.selected ?? top.place} 결과로 돌아가기</span>
    </button>
  );
}

// ---------- 시작 ----------
function PanelHome() {
  return (
    <>
      <div className="hero-art">
        <Svg src={ART.heroBanner} className="scene" alt="한라산과 바다를 배경으로 선 돌하르방과 귤" />
      </div>
      <div className="hello">
        <h2>우리 가족이 갈 수 있을까?</h2>
        <p>경사·턱·화장실을 미리 확인해 드려요.</p>
      </div>
      <ul className="choices">
        {TYPES.map(([label, icon, ut, text, desc, bg]) => (
          <li key={ut} className="choice-card">
            <div className="choice">
              <div className="ic" style={{ background: bg }}>
                <Svg src={ICON_URI[icon]} />
              </div>
              <div>
                <b>{label}</b>
                <span>{desc}</span>
              </div>
            </div>
            <button type="button" className="btn btn-primary" onClick={() => go(text, ut, false, true)} aria-label={`${label} 갈 곳 찾기`}>
              <span>찾기</span>
              <Icon name="arrow_forward" />
            </button>
          </li>
        ))}
      </ul>
    </>
  );
}

const ICON_URI: Record<string, string> = Object.fromEntries(Object.entries(ICON).map(([k, v]) => [k, dataUri(v)]));

// ---------- 결과: 한눈에 ----------
function WeatherLine({ place, when }: { place: string; when: string }) {
  const w = useApi<Weather>(urls.weather(place, when));
  const wx = w.data ?? {};
  if (!wx.available) return null; // 예보 값이 비어 있으면 날씨 줄만 빼고 보여 준다
  const rain = wx.rain_chance === null || wx.rain_chance === undefined ? "확인 안 됨" : `${wx.rain_chance}%`;
  const wind = wx.wind_ms === null || wx.wind_ms === undefined ? "확인 안 됨" : `${wx.wind_ms.toFixed(0)}m/s`;
  const md = /^\d{4}-(\d{2})-(\d{2})$/.exec(wx.date ?? "");
  const day = md ? `${Number(md[1])}/${Number(md[2])}` : wx.date;
  const line = `${day} 비 올 확률 ${rain} · 바람 ${wind} · ${wx.temp}`;
  return <WeatherBox line={line} tips={wx.tips ?? []} />;
}

/** 코스 조사 자료가 있는 곳인지(관광공사 시설 자료는 경사·코스 길이가 없다) */
const hasCourse = (p: { minutes?: number | null; course_m?: number | null }) => !!p.minutes && !!p.course_m;

/** 관광공사 출입 경로 문장을 칸에 맞게 짧게 */
const entryShort = (st: string) =>
  /턱이 없|턱 없|단차 없/.test(st) ? "턱 없음" : /경사로/.test(st) ? "경사로 있음" : /계단|턱이 있|단차/.test(st) ? "턱·계단 있음" : "있어요";

/** 자료가 있는 칸만 보여 준다('기록 없음', 'null분' 칸을 만들지 않는다) */
function overviewTiles(top: PlaceResult): [string, string, string][] {
  const t: [string, string, string][] = [];
  if (top.slope_level && top.slope_level !== "기록 없음") {
    t.push(["경사", top.slope_level, top.slope_level === "완만한 편" ? "yes" : ""]);
  }
  if (hasCourse(top)) t.push(["코스", `약 ${top.minutes}분 · ${fmt(top.course_m)}m`, ""]);
  const entry = (top.checks ?? []).find((c) => c.item.includes("출입"));
  if (!hasCourse(top) && entry) t.push(["출입구", entry.known ? entryShort(entry.status) : "확인 안 됨", entry.known ? "yes" : "no"]);
  t.push(["장애인 화장실", top.accessible_toilet ? "있어요" : "확인 안 됨", top.accessible_toilet ? "yes" : "no"]);
  t.push(["장애인 주차", top.accessible_parking === "yes" ? "있어요" : "확인 안 됨", top.accessible_parking === "yes" ? "yes" : "no"]);
  return t;
}

function Overview({ s, top, det }: { s: State; top: PlaceResult; det?: Detail }) {
  const warn = [...(top.watch_out ?? [])];
  if (top.companion_advised) warn.unshift("동행인과 함께 가는 것을 권해요");
  const tiles = overviewTiles(top);
  return (
    <>
      <PlaceHead name={top.place} where={top.where} />
      <VerdictWithEvidence key={top.place} color={top.verdict_color} label={top.verdict} reason={top.verdict_reason}
        evidence={top.evidence ?? det?.evidence} />
      <div className={`tiles-wrap n${tiles.length}`}><Tiles items={tiles} /></div>
      <Notes good={top.good_points ?? []} warn={warn} />
      <WeatherLine place={top.place} when={s.when} />
      <BusLine stops={det?.bus_stops} />
      <div className="row actions">
        <LinkButton href={kakaoRouteLink(top.place, top.lat, top.lon)} icon="directions" kind="primary">
          길안내
        </LinkButton>
        {hasCourse(top) && (
          <button type="button" className="btn btn-secondary" onClick={() => setTab("코스")}>
            <Icon name="route" /><span>코스 보기</span>
          </button>
        )}
        {top.phone && <LinkButton href={`tel:${top.phone}`} icon="call">전화하기</LinkButton>}
      </div>
      <Src>
        자료: {hasCourse(top) ? `제주데이터허브 무장애여행 정보(${det?.base_date ?? top.base_date} 기준)` : "한국관광공사 무장애 여행 정보(입구·편의시설 기준)"}
        {det?.bus_stops?.length ? ", 버스 정류소 정보(직선거리)" : ""}, 날씨 예보(Open-Meteo). 현장과 다를 수 있어요.
      </Src>
    </>
  );
}

// ---------- 결과: 코스 ----------
function Course({ top, det, failed }: { top: PlaceResult; det?: Detail; failed: boolean }) {
  if (!det) return failed ? <Caption>코스 정보를 불러오지 못했어요. 잠시 뒤 다시 열어 주세요.</Caption> : <Loading />;
  const bits = [
    hasCourse(det) ? `약 ${det.minutes}분 · ${fmt(det.course_m)}m` : "",
    det.slope_level && det.slope_level !== "기록 없음" ? `경사 ${det.slope_level}` : "",
  ].filter(Boolean);
  const toilets = det.toilets_near ?? [];
  return (
    <>
      <PlaceHead name={top.place} where={bits.join(" · ") || top.where} />
      {hasCourse(det) ? (
        <>
          <Sect>코스 따라가기</Sect>
          {det.key_points.length ? (
            <>
              <Caption>지도에 ⚠️로 표시한 곳은 천천히 지나가세요.</Caption>
              <Timeline points={det.key_points} notCaution={NOT_CAUTION} />
            </>
          ) : <Caption>코스에 조심할 곳으로 기록된 지점은 없어요.</Caption>}
        </>
      ) : (
        <Info>이곳은 코스 조사 자료가 없어요. 입구와 편의시설 정보는 한눈에 탭에서 볼 수 있어요.</Info>
      )}
      {toilets.length > 0 && (
        <>
          <Sect>가까운 장애인 화장실</Sect>
          <ul className="cards">
            {toilets.map((t, i) => (
              <li key={`wc-${i}`} className="card">
                <Shop name={t.name} meta={[t.km ? `${t.km}km` : "바로 옆", t.address ?? ""].join(" · ")} tags={[]} />
                {t.phone && (
                  <div className="row">
                    <LinkButton href={`tel:${t.phone}`} icon="call">전화 {t.phone}</LinkButton>
                  </div>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
      <Src>{det.source}</Src>
    </>
  );
}

// ---------- 결과: 식당 ----------
const OPEN_STATUS: Record<string, [string, string]> = {
  "영업 확인": ["2025 영업 확인", "wc"], "확인 안 됨": ["영업 확인 안 됨", "gray"], "폐업 기록": ["폐업 기록", "red"],
};

function FoodTab({ s, top }: { s: State; top: PlaceResult }) {
  const own = s.food && s.food.around === top.place ? s.food : null;
  const fetched = useApi<Food>(own ? null : urls.food(top.place, s.user_type.includes("wheelchair")));
  const near = useApi<Nearby>(urls.nearby(top.place));
  const f = own ?? fetched.data;
  const cond = (f?.diet_labels ?? []).join(" · ");
  return (
    <>
      <Sect>{top.place} 근처 {cond || "식당"}</Sect>
      {f ? <FoodList f={f} focus={s.focus} /> : fetched.error ? <Caption>식당 정보를 불러오지 못했어요.</Caption> : <Loading />}
      {near.data && near.data.items.length > 0 && (
        <details className="expander">
          <summary><Icon name="storefront" /><span>이 장소 주변 가게 (2021 조사)</span><Icon name="expand_more" /></summary>
          <ul className="cards">
            {near.data.items.map((it, i) => {
              const tags: [string, string][] = [OPEN_STATUS[it.open_status] ?? [it.open_status, "gray"]];
              if (it.wheelchair_entry) tags.push(["휠체어 진입", "wc"]);
              return (
                <li key={i} className="card">
                  <Shop name={it.name} meta={`${it.category} · ${it.km}km`} tags={tags} />
                </li>
              );
            })}
          </ul>
          <Src>{near.data.note}</Src>
        </details>
      )}
    </>
  );
}

function HelpTab({ s, top }: { s: State; top: PlaceResult }) {
  const h = useApi<Help>(urls.help(top.place));
  return (
    <>
      <Sect>{top.place}에서 가까운 곳</Sect>
      {h.data ? <HelpList h={h.data} focus={s.focus} /> : h.error ? <Caption>병원·약국 정보를 불러오지 못했어요.</Caption> : <Loading />}
    </>
  );
}

function Tabs({ tab }: { tab: Tab }) {
  const onKey = (e: KeyboardEvent<HTMLDivElement>) => {
    const i = TABS.indexOf(tab);
    const n = e.key === "ArrowRight" ? i + 1 : e.key === "ArrowLeft" ? i - 1 : e.key === "Home" ? 0 : e.key === "End" ? TABS.length - 1 : null;
    if (n === null) return;
    e.preventDefault();
    const next = TABS[(n + TABS.length) % TABS.length];
    setTab(next);
    document.getElementById(`tab-${next}`)?.focus();
  };
  return (
    <div className="tabs" role="tablist" aria-label="화면" onKeyDown={onKey}>
      {TABS.map((t) => (
        <button key={t} id={`tab-${t}`} type="button" role="tab" className="tab" aria-selected={t === tab}
          aria-controls="tabpanel" tabIndex={t === tab ? 0 : -1} onClick={() => setTab(t)}>
          {t}
        </button>
      ))}
    </div>
  );
}

/** 패널 맨 위: 지금 조건(이동 유형·날짜·동네)을 한 줄 글자로. tag는 화면 읽기 프로그램용 */
function Head({ s, tag, userTypes }: { s: State; tag: string; userTypes?: Record<string, string> }) {
  const chips = conditionTexts(s, userTypes ?? USER_TYPES);
  return (
    <p className="dash-head">
      <span className="sr-only">{tag}: </span>
      {chips.join(" · ")}
    </p>
  );
}

/** 추천 후보 번호 단추(지도 번호와 같다) + 본 곳 빼고 새로 찾기 */
function Candidates({ s, top }: { s: State; top: PlaceResult }) {
  const results = s.results?.results ?? [];
  return (
    <div className="cands" role="group" aria-label={`추천 ${results.length}곳`}>
      {results.map((r, i) => (
        <button key={r.place} type="button" className="cand" aria-pressed={r.place === top.place}
          onClick={() => pick(r.place)} title={`${i + 1}번 · ${r.place} · ${r.verdict}`}>
          <i style={{ background: VERDICT_HEX[r.verdict_color] ?? "#5F6B73" }} aria-hidden="true">{i + 1}</i>
          <span>{r.place}</span>
        </button>
      ))}
      <button type="button" className="cand renew" onClick={() => go("다른 곳 추천해 줘")} disabled={!!s.pending}
        aria-label="본 곳 빼고 새로 찾기" title="본 곳 빼고 새로 찾기">
        <Icon name="autorenew" />
      </button>
    </div>
  );
}

function PanelResult({ s, userTypes }: { s: State; userTypes?: Record<string, string> }) {
  const top = topPlace(s);
  const d = useApi<Detail | { error: string }>(top ? urls.detail(top.place, s.user_type) : null);
  if (!top) return <Info>조건에 맞는 곳을 더 찾지 못했어요. 동네나 분위기를 바꿔서 말해 보세요.</Info>;
  const det = d.data && !isError(d.data) ? d.data : undefined;
  const failed = !!d.error || (!!d.data && isError(d.data));
  return (
    <>
      <Head s={s} tag="추천 결과" userTypes={userTypes} />
      <Candidates s={s} top={top} />
      <Tabs tab={s.tab} />
      <div id="tabpanel" role="tabpanel" aria-labelledby={`tab-${s.tab}`} className="tabpanel">
        {s.tab === "한눈에" && <Overview s={s} top={top} det={det} />}
        {s.tab === "코스" && <Course top={top} det={det} failed={failed} />}
        {s.tab === "식당" && <FoodTab s={s} top={top} />}
        {s.tab === "병원·약국" && <HelpTab s={s} top={top} />}
      </div>
    </>
  );
}

// ---------- 식당 ----------
function PanelFood({ s, f, userTypes }: { s: State; f: Food; userTypes?: Record<string, string> }) {
  const cond = (f.diet_labels ?? []).join(" · ");
  return (
    <>
      <Head s={s} tag={`식당 ${(f.items ?? []).length}곳`} userTypes={userTypes} />
      <BackButton s={s} />
      <Sect>{f.around} 근처 {cond || f.food_kind || "식당"}</Sect>
      <FoodList f={f} focus={s.focus} />
    </>
  );
}

// ---------- 장소·병원 답 ----------
function PanelAnswer({ s, userTypes }: { s: State; userTypes?: Record<string, string> }) {
  const d = s.detail_only && "verdict" in s.detail_only ? s.detail_only : null;
  return (
    <>
      <Head s={s} tag="장소 정보" userTypes={userTypes} />
      <BackButton s={s} />
      {d && (
        <>
          <VerdictWithEvidence key={d.place} color={d.verdict_color} label={d.verdict} reason={d.verdict_reason}
            evidence={d.evidence} />
          <PlaceHead name={d.place} where={d.where} />
          <Sect>시설 정보</Sect>
          <Checks rows={d.checks} />
          {d.key_points.length > 0 && (
            <>
              <Sect>코스 따라가기</Sect>
              <Timeline points={d.key_points} notCaution={NOT_CAUTION} />
            </>
          )}
        </>
      )}
      {s.help_only && (
        <>
          <Sect>{s.help_only.place}에서 가까운 곳</Sect>
          <HelpList h={s.help_only} focus={s.focus} />
        </>
      )}
    </>
  );
}

// ---------- 틀 ----------
export default function Dashboard({ s, userTypes }: { s: State; userTypes?: Record<string, string> }) {
  const box = useRef<HTMLElement>(null);
  const scroller = useRef<HTMLDivElement>(null);
  const drag = useRef<{ y: number; h: number; moved: boolean } | null>(null);
  const skipClick = useRef(false);

  // 보이는 내용이 바뀌면 맨 위부터
  useEffect(() => {
    scroller.current?.scrollTo({ top: 0 });
  }, [s.screen, s.tab, s.selected]);

  if (!s.panel_open) return null;

  // 휴대폰 아래 시트: 손잡이를 끌어 올리면 크게, 내리면 작게, 더 내리면 숨긴다. 누르면 크게/작게.
  const onDown = (e: PointerEvent<HTMLButtonElement>) => {
    if (!box.current) return;
    drag.current = { y: e.clientY, h: box.current.getBoundingClientRect().height, moved: false };
    e.currentTarget.setPointerCapture(e.pointerId);
  };
  const onMove = (e: PointerEvent<HTMLButtonElement>) => {
    const d = drag.current;
    if (!d || !box.current) return;
    const dy = e.clientY - d.y;
    if (Math.abs(dy) > 6) d.moved = true;
    if (!d.moved) return;
    const max = window.innerHeight - 72;
    box.current.style.transition = "none";
    box.current.style.height = `${Math.max(96, Math.min(max, d.h - dy))}px`;
  };
  const onUp = (e: PointerEvent<HTMLButtonElement>) => {
    const d = drag.current;
    drag.current = null;
    if (!d || !box.current) return;
    const h = box.current.getBoundingClientRect().height;
    box.current.style.transition = "";
    box.current.style.height = "";
    if (!d.moved) return; // 그냥 누른 것은 onClick 이 처리한다(키보드도 같은 길)
    skipClick.current = true;
    const vh = window.innerHeight;
    if (h < vh * 0.28) {
      togglePanel();
    } else {
      setSheet(h > vh * 0.66 ? "full" : "half");
    }
    e.currentTarget.releasePointerCapture?.(e.pointerId);
  };
  const onClick = () => {
    if (skipClick.current) {
      skipClick.current = false;
      return;
    }
    setSheet(s.sheet === "full" ? "half" : "full");
  };
  const onCancel = () => {
    drag.current = null;
    if (box.current) {
      box.current.style.transition = "";
      box.current.style.height = "";
    }
  };

  let body;
  let label = "시작";
  if (s.screen === "result" && s.results) {
    body = <PanelResult s={s} userTypes={userTypes} />;
    label = "추천 결과";
  } else if (s.screen === "food" && s.food) {
    body = <PanelFood s={s} f={s.food} userTypes={userTypes} />;
    label = "식당";
  } else if (s.screen === "answer" && (s.detail_only || s.help_only)) {
    body = <PanelAnswer s={s} userTypes={userTypes} />;
    label = "장소 정보";
  } else {
    body = <PanelHome />;
  }

  return (
    <section ref={box} className="dash" aria-label={`대시보드: ${label}`}>
      <button type="button" className="sheet-handle" onPointerDown={onDown} onPointerMove={onMove} onPointerUp={onUp}
        onPointerCancel={onCancel} onClick={onClick} aria-label={s.sheet === "full" ? "패널 작게 보기" : "패널 크게 보기"}
        aria-expanded={s.sheet === "full"}>
        <span />
      </button>
      <div ref={scroller} className="dash-scroll">
        {body}
      </div>
    </section>
  );
}
