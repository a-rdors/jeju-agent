"use client";
// 오른쪽 대시보드(휴대폰은 아래 시트). 시작 / 결과(한눈에·코스·식당·병원·약국) / 식당 / 장소·병원 답.
import { useEffect, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import { NOT_CAUTION, VERDICT_HEX } from "@/lib/mapData";
import { ART, ICON, dataUri } from "@/lib/art";
import { USER_TYPES, isError, kakaoRouteLink, urls } from "@/lib/api";
import type { Detail, Evidence, Food, Help, Nearby, PlaceResult, Weather } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import {
  TABS, backHome, conditionTexts, focusItem, go, pick, setLocation, setMapView, setSheet, setTab, toResult, togglePanel, topPlace,
  type State, type Tab,
} from "@/lib/store";
import {
  Caption, Checks, Info, LinkButton, Loading, PlaceHead, Sect, Shop, Src, Svg, Timeline,
} from "./bits";
import { EvidenceList, VerdictWithEvidence } from "./Evidence";
import Icon from "./Icon";

// (버튼 글자, 아이콘, 이동 유형, 보낼 문장, 설명)
const TYPES: [string, string, string, string, string][] = [
  ["휠체어 타는 가족", "wheel", "manual_wheelchair", "휠체어 타는 가족과 나들이 갈 곳 추천해 줘", "턱 없는 입구 · 장애인 화장실"],
  ["아기와 유모차", "stroller", "stroller", "유모차 끌고 갈 만한 곳 추천해 줘", "계단 없는 길 · 수유실"],
  ["걷기 힘든 어르신", "senior", "senior", "부모님 모시고 가볍게 다녀올 곳 추천해 줘", "짧고 완만한 길 · 쉴 곳"],
  ["임신 중인 가족", "pregnant", "pregnant", "임신 중이라 무리 없이 다녀올 곳 추천해 줘", "평평한 길 · 가까운 병원"],
];

// 시작 화면 '어디쯤 가세요?' (보이는 글자, 질문에 붙일 동네 말, 지도 가운데). 고르지 않으면 제주 전체
const AREAS: [string, string, [number, number] | null][] = [
  ["상관없어요", "", null],
  ["제주시", "제주시", [33.49, 126.53]],
  ["애월·한림", "애월", [33.42, 126.31]],
  ["중문·서귀포", "서귀포", [33.255, 126.49]],
  ["성산·구좌", "성산", [33.47, 126.85]],
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

/** 길안내·전화·지도: 같은 크기로 한 줄(길안내만 주황) */
function Acts({ name, lat, lon, phone, map = true }: { name: string; lat: number; lon: number; phone?: string; map?: boolean }) {
  return (
    <div className="acts">
      <LinkButton href={kakaoRouteLink(name, lat, lon)} icon="directions" kind="primary">길안내</LinkButton>
      {phone && <LinkButton href={`tel:${phone}`} icon="call">전화</LinkButton>}
      {map && <MapButton name={name} />}
    </div>
  );
}

function ShopCard({ it, focus, ut = "other" }: { it: Food["items"][number]; focus?: string | null; ut?: string }) {
  const tags: [string, string][] = it.wheelchair_entry ? [[isWheel(ut) ? "휠체어 진입 확인(2021)" : "입구 턱 없음(2021 조사)", "wc"]] : [];
  tags.push(...(it.why ?? []).map((w): [string, string] => [w.split(":")[0] + " (추정)", ""]));
  const meta = [it.food_type, it.km !== null && it.km !== undefined ? `${it.km}km` : "", it.phone ?? ""].filter(Boolean).join(" · ");
  return (
    <FocusCard name={it.name} focus={focus}>
      <Shop name={it.name} meta={meta} tags={tags} />
      <Acts name={it.name} lat={it.lat} lon={it.lon} phone={it.phone} />
    </FocusCard>
  );
}

function FoodList({ f, focus, ut }: { f: Food; focus?: string | null; ut?: string }) {
  if (f.anchor_not_found) return <Info>{f.note}</Info>;
  return (
    <>
      {!f.items.length && <Info>조건에 맞는 식당을 찾지 못했어요. 조건을 줄이거나 동네를 바꿔 말해 보세요.</Info>}
      {f.items.length > 0 && (
        <ul className="cards">
          {f.items.map((it, i) => <ShopCard key={`${it.name}-${i}`} it={it} focus={focus} ut={ut} />)}
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
              <Shop name={it.name} meta={[kind, it.km !== null && it.km !== undefined ? `${it.km}km` : "", it.phone, it.address].filter(Boolean).join(" · ")}
                tags={it.status ? [[it.status, "wc"]] : []} />
              <Acts name={it.name} lat={it.lat} lon={it.lon} phone={it.phone} />
            </FocusCard>
          )),
        )}
      </ul>
      <Src>직선거리 기준 · 응급 시 119</Src>
    </>
  );
}

function BackButton({ s }: { s: State }) {
  const top = topPlace(s);
  if (!top) {
    return (
      <button type="button" className="btn btn-tertiary back" onClick={backHome}>
        <Icon name="arrow_back" />
        <span>처음 화면으로</span>
      </button>
    );
  }
  return (
    <button type="button" className="btn btn-tertiary back" onClick={toResult}>
      <Icon name="arrow_back" />
      <span>{s.selected ?? top.place} 결과로 돌아가기</span>
    </button>
  );
}

/** 식당 목록 제목: '제주공항 근처 흑돼지·고기', 기준이 없으면 '제주 전체에서 찾은 흑돼지·고기' */
function foodTitle(around: string | null | undefined, what: string) {
  if (!around || around === "제주 전체") return `제주 전체에서 찾은 ${what}`;
  if (around === "현재 위치") return `내 근처 ${what}`;
  return `${around} 근처 ${what}`;
}

// ---------- 시작 ----------
// '내 위치'는 지도 왼쪽 단추(Locate.tsx)로 정한다. 위치가 있고 동네를 고르지 않았으면 내 근처로 찾는다.
function PanelHome({ s }: { s: State }) {
  const [area, setArea] = useState("");
  const near = !!s.location && !area;
  const pickArea = (word: string, at: [number, number] | null) => {
    setLocation(null);
    setArea(word);
    setMapView(at ? { lat: at[0], lon: at[1], level: 8 } : { all: true });
  };
  return (
    <>
      <div className="hero-art">
        <Svg src={ART.heroBanner} className="scene" alt="한라산과 바다를 배경으로 선 돌하르방과 귤" />
      </div>
      <div className="hello">
        <h2>함께 가도 괜찮을지,<br />먼저 알려 드려요</h2>
        <p>입구·길·화장실부터 식당·병원까지 확인해요.</p>
      </div>
      <div className="where">
        <p><b>어디쯤 가세요?</b> <span>고르지 않아도 돼요</span></p>
        <div className="where-chips" role="radiogroup" aria-label="어디쯤 가세요">
          {AREAS.map(([label, word, at]) => (
            <button key={label} type="button" role="radio" aria-checked={area === word && !(word === "" && near)} className="wchip"
              onClick={() => pickArea(word, at)}>{label}</button>
          ))}
        </div>
        {near && (
          <p className="where-note" role="status">
            <Icon name="my_location" />
            <span>현재 위치를 기준으로 가까운 곳부터 찾아 드릴게요.</span>
          </p>
        )}
      </div>
      <ul className="choices">
        {TYPES.map(([label, icon, ut, text, desc]) => (
          <li key={ut} className="choice-card">
            <div className="choice">
              <div className="ic">
                <Svg src={ICON_URI[icon]} />
              </div>
              <div>
                <b>{label}</b>
                <span>{desc}</span>
              </div>
            </div>
            <button type="button" className="btn btn-primary" onClick={() => go(near ? `내 근처 ${text}` : area ? `${area} 쪽 ${text}` : text, ut, false, true)} aria-label={`${label} 갈 곳 찾기`}>
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

// ---------- 결과: 한눈에 (요약 목록형) ----------
// 색은 뜻별로 네 가지만: 초록=가능·있음, 주황=조심, 파랑=날씨, 회색=참고
function WeatherLine({ place, when, alt }: { place: string; when: string; alt?: string }) {
  const w = useApi<Weather>(urls.weather(place, when));
  const wx = w.data ?? {};
  if (!wx.available) return null; // 예보 값이 비어 있으면 날씨 줄만 빼고 보여 준다
  const md = /^\d{4}-(\d{2})-(\d{2})$/.exec(wx.date ?? "");
  const day = md ? `${Number(md[1])}/${Number(md[2])}` : wx.date;
  const rainy = (wx.rain_chance ?? 0) >= 50;
  const rain = wx.rain_chance === null || wx.rain_chance === undefined ? "" : `비 ${wx.rain_chance}%`;
  return (
    <div className="line info">
      <Icon name={rainy ? "umbrella" : "sun"} />
      <span>
        {[day, rain, wx.temp].filter(Boolean).join(" · ")}
        {rainy && alt && <> · 실내라면 <b>{alt}</b></>}
      </span>
    </div>
  );
}

/** 코스 조사 자료가 있는 곳인지(관광공사 시설 자료는 경사·코스 길이가 없다) */
const hasCourse = (p: { minutes?: number | null; course_m?: number | null }) => !!p.minutes && !!p.course_m;

/** 관광공사 출입 경로 문장을 짧게 */
const entryShort = (st: string) =>
  /턱이 없|턱 없|단차 없/.test(st) ? "턱 없음" : /경사로/.test(st) ? "경사로 있음" : /계단|턱이 있|단차/.test(st) ? "턱·계단 있음" : "정보 있음";

type Fact = [string, string, boolean];
// 있으면 좋은 것: 아이콘 이름(lib/icons.ts)
const EXTRA_ICON: [RegExp, string][] = [
  [/휠체어를 빌릴/, "wheelchair"], [/유모차를 빌릴/, "stroller"], [/수유실/, "check"], [/쉬어 갈 곳/, "seat"], [/분위기/, "check"],
];

const isWheel = (ut: string) => ut === "manual_wheelchair" || ut === "electric_wheelchair";
/** 휠체어를 말하지 않은 사람에게는 '장애인' 대신 일상어(장애인 주차구역은 표지가 있어야 쓸 수 있어 '주차장') */
const facName = (ut: string, what: "toilet" | "parking") =>
  what === "toilet" ? (isWheel(ut) ? "장애인 화장실" : "넓은 화장실") : (isWheel(ut) ? "장애인 주차" : "주차장");
const neutralText = (ut: string, t: string) =>
  isWheel(ut) ? t : t.replace(/장애인 화장실/g, "넓은 화장실").replace(/장애인 주차구역|장애인 주차/g, "주차장");

const neutralPoints = <T extends { flags: string[]; label: string }>(ut: string, pts: T[]): T[] =>
  pts.map((p) => ({ ...p, label: neutralText(ut, p.label), flags: p.flags.map((f) => neutralText(ut, f)) }));

/** 한 줄씩 훑어 읽는 시설 목록(같은 말을 칸과 목록에 두 번 쓰지 않는다) */
function overviewFacts(top: PlaceResult, ut: string): Fact[] {
  const f: Fact[] = [];
  const entry = (top.checks ?? []).find((c) => c.item.includes("출입"));
  if (hasCourse(top)) {
    const known = !!top.slope_level && top.slope_level !== "기록 없음";
    f.push(["slope", known ? `길 경사 ${top.slope_level}` : "길 경사 기록 없음", top.slope_level === "완만한 편"]);
    f.push(["schedule", `코스 약 ${top.minutes}분 · ${fmt(top.course_m)}m`, true]);
  } else if (entry) {
    f.push(["wheelchair", entry.known ? `입구 ${entryShort(entry.status)}` : "입구 정보 없음", entry.known]);
  }
  f.push(["wc", `${facName(ut, "toilet")} ${top.accessible_toilet ? "있음" : "확인 안 됨"}`, !!top.accessible_toilet]);
  f.push(["parking", `${facName(ut, "parking")} ${top.accessible_parking === "yes" ? "있음" : "확인 안 됨"}`, top.accessible_parking === "yes"]);
  for (const g of top.good_points ?? []) {
    const ic = EXTRA_ICON.find(([re]) => re.test(g));
    if (ic) f.push([ic[1], g, true]);
  }
  if (!hasCourse(top)) f.push(["slope", "길 경사 조사 자료 없음", false]);
  return f;
}

const VERDICT_CLS: Record<string, string> = { green: "ok", orange: "warn", red: "warn", gray: "gray" };

/** 판정 알약 + 근거 보기(판정 뒤 공공데이터 조사 원문) */
function VerdictPill({ color, label, evidence }: { color: string; label: string; evidence?: Evidence | null }) {
  const [open, setOpen] = useState(false);
  const has = !!evidence && evidence.items.length > 0;
  return (
    <>
      <div className="vrow">
        <span className={`vpill ${VERDICT_CLS[color] ?? "gray"}`}>{color === "green" && <Icon name="check" />}{label}</span>
        {has && (
          <button type="button" className="ev-toggle" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
            {open ? "근거 닫기" : evidence!.kind === "course" ? `근거 보기 · 조사 지점 ${evidence!.items.length}곳` : "근거 보기"}
          </button>
        )}
      </div>
      {has && open && <EvidenceList ev={evidence!} />}
    </>
  );
}

function Overview({ s, top, det }: { s: State; top: PlaceResult; det?: Detail }) {
  const warn = [...(top.watch_out ?? [])];
  if (top.companion_advised) warn.unshift("동행인과 함께 가는 것을 권해요");
  if (top.verdict_color !== "green" && top.verdict_reason) warn.unshift(top.verdict_reason);
  if (!hasCourse(top)) warn.push("길 경사는 확인이 안 돼요. 가기 전에 전화해 보세요.");
  const facts = overviewFacts(top, s.user_type);
  const bus = det?.bus_stops?.[0];
  const alt = (top as PlaceResult & { rain_alt?: { name: string } }).rain_alt?.name;
  return (
    <>
      <div className="r-head">
        <h2 className="place-name">{top.place}</h2>
        <span className="place-where">{top.where}</span>
      </div>
      <VerdictPill key={top.place} color={top.verdict_color} label={top.verdict} evidence={top.evidence ?? det?.evidence} />
      <ul className="facts">
        {facts.map(([ic, text, yes], i) => (
          <li key={i} className={yes ? "y" : "n"}><Icon name={ic} /><span>{text}</span></li>
        ))}
      </ul>
      {warn.slice(0, 2).map((w, i) => (
        <div key={i} className="line warn"><Icon name="warning" /><span><span className="sr-only">조심할 점: </span>{neutralText(s.user_type, w)}</span></div>
      ))}
      <WeatherLine place={top.place} when={s.when} alt={alt} />
      <details className="more-d">
        <summary>
          <span>{bus ? <><Icon name="bus" />{bus.name} 정류소 {fmt(bus.m)}m</> : "시설 정보"}</span>
          <span className="more-go">자세히 ›</span>
        </summary>
        <Checks rows={(top.checks ?? []).map((c) => ({ ...c, item: neutralText(s.user_type, c.item), status: neutralText(s.user_type, c.status) }))} />
        <Src>
          자료: {hasCourse(top) ? `제주데이터허브 무장애여행 정보(${det?.base_date ?? top.base_date} 기준)` : "한국관광공사 무장애 여행 정보(입구·편의시설 기준)"}
          {bus ? ", 버스 정류소 정보(직선거리)" : ""}, 날씨 예보(Open-Meteo). 현장과 다를 수 있어요.
        </Src>
      </details>
      <div className="acts">
        <LinkButton href={kakaoRouteLink(top.place, top.lat, top.lon)} icon="directions" kind="primary">길안내</LinkButton>
        {top.phone && <LinkButton href={`tel:${top.phone}`} icon="call">전화</LinkButton>}
        {hasCourse(top) && (
          <button type="button" className="btn btn-secondary" onClick={() => setTab("코스")}>
            <Icon name="route" /><span>코스</span>
          </button>
        )}
      </div>
    </>
  );
}

// ---------- 결과: 코스 ----------
function Course({ top, det, failed, ut = "other" }: { top: PlaceResult; det?: Detail; failed: boolean; ut?: string }) {
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
              <Caption>지도에 빨간 ! 로 표시한 곳은 천천히 지나가세요.</Caption>
              <Timeline points={neutralPoints(ut, det.key_points)} notCaution={NOT_CAUTION} />
            </>
          ) : <Caption>코스에 조심할 곳으로 기록된 지점은 없어요.</Caption>}
        </>
      ) : (
        <Info>이곳은 코스 조사 자료가 없어요. 입구와 편의시설 정보는 한눈에 탭에서 볼 수 있어요.</Info>
      )}
      {toilets.length > 0 && (
        <>
          <Sect>가까운 {facName(ut, "toilet")}</Sect>
          <ul className="cards">
            {toilets.map((t, i) => (
              <li key={`wc-${i}`} className="card">
                <Shop name={t.name}
                  meta={[t.km ? `${t.km}km` : "바로 옆", t.address ?? ""].join(" · ")}
                  tags={[
                    ...(t.accessible_count ? [[`${isWheel(ut) ? "장애인" : "넓은"} 칸 ${t.accessible_count}개`, "wc"] as [string, string]] : []),
                    ...(t.diaper ? [["기저귀 교환대", ""] as [string, string]] : []),
                  ]} />
                {t.phone && (
                  <div className="acts">
                    <LinkButton href={`tel:${t.phone}`} icon="call">관리기관 전화</LinkButton>
                  </div>
                )}
              </li>
            ))}
          </ul>
          <Src>공중화장실 정보(제주특별자치도). 전화번호는 화장실을 관리하는 기관 번호예요.</Src>
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
      <Sect>{foodTitle(top.place, cond || "식당")}</Sect>
      {f ? <FoodList f={f} focus={s.focus} ut={s.user_type} /> : fetched.error ? <Caption>식당 정보를 불러오지 못했어요.</Caption> : <Loading />}
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
          <i style={{ background: VERDICT_HEX[r.verdict_color] ?? VERDICT_HEX.gray }} aria-hidden="true">{i + 1}</i>
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
        {s.tab === "코스" && <Course top={top} det={det} failed={failed} ut={s.user_type} />}
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
      <Sect>{foodTitle(f.around, cond || f.food_kind || "식당")}</Sect>
      <FoodList f={f} focus={s.focus} ut={s.user_type} />
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
          <Checks rows={d.checks.map((c) => ({ ...c, item: neutralText(s.user_type, c.item), status: neutralText(s.user_type, c.status) }))} />
          {d.key_points.length > 0 && (
            <>
              <Sect>코스 따라가기</Sect>
              <Timeline points={neutralPoints(s.user_type, d.key_points)} notCaution={NOT_CAUTION} />
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

  // 패널(휴대폰 아래 시트)의 실제 높이를 --dash-h 로 알려 하르방 단추·말풍선이 끌어올리는 대로 따라오게 한다.
  // 시트가 높아 위쪽에 단추 둘 자리(상단 바 아래 약 170px)가 없으면 sheet-tall 을 달아
  // 내 위치 단추·말풍선은 숨기고 하르방 단추는 시트 위 오른쪽 아래로 내린다(시트와 겹치지 않게).
  useEffect(() => {
    const root = document.documentElement;
    const el = box.current;
    if (!el || typeof ResizeObserver === "undefined") {
      root.style.setProperty("--dash-h", "0px");
      return;
    }
    const ro = new ResizeObserver(() => {
      const h = Math.round(el.getBoundingClientRect().height);
      root.style.setProperty("--dash-h", `${h}px`);
      root.classList.toggle("sheet-tall", window.innerHeight - h < 170);
    });
    ro.observe(el);
    return () => {
      ro.disconnect();
      root.style.setProperty("--dash-h", "0px");
      root.classList.remove("sheet-tall");
    };
  }, [s.panel_open]);

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
    body = <PanelHome s={s} />;
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
