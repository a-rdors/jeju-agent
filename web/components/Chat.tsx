"use client";
// 오른쪽 아래 하르방 버튼과 대화창 (main.py chat_fab(), chat_window(), bot_msg())
import { useEffect, useRef, useState, type FormEvent } from "react";
import { ART } from "@/lib/art";
import { closeChat, focusItem, go, locateAndRetry, resultNames, showPlace, toggleChat, typingDone, type Msg, type State } from "@/lib/store";
import { kakaoRouteLink } from "@/lib/api";
import { Avatar, LinkButton, Svg } from "./bits";
import Icon from "./Icon";
import Markdown from "./Markdown";

// 빈 대화창에 보이는 예시(그림, 말)
const EXAMPLES: [string, string][] = [
  ["♿", "휠체어 타는 아빠랑 바다 보러"],
  ["👶", "유모차로 비 오는 날 실내"],
  ["🍲", "할머니 드시기 편한 식당"],
  ["🚻", "근처 장애인 화장실"],
];
const GREETING = "안녕하세요, 하르방 도우미예요. 누구와 가는지 말해 주시면 **그분이 갈 수 있는 곳**만 골라 드려요.";
// 기다리는 동안 보여 줄 말. 질문 종류에 맞춰 고른다(응급실을 물었는데 '경사 계산 중'이 뜨지 않게).
const LOADING_STEPS = {
  help: ["가까운 병원·약국을 찾고 있어요", "응급실 위치를 확인하고 있어요", "장애인 화장실을 찾고 있어요"],
  food: ["가까운 식당을 찾고 있어요", "식사 조건을 맞춰 보고 있어요", "들어가기 편한지 보고 있어요"],
  weather: ["날씨를 확인하고 있어요", "비 오면 갈 곳을 찾고 있어요", "갈 만한 곳을 고르고 있어요"],
  place: ["갈 만한 곳을 찾고 있어요", "경사와 턱을 살펴보고 있어요", "화장실과 쉴 곳을 찾고 있어요"],
  other: ["말씀을 살펴보고 있어요", "필요한 정보를 찾고 있어요", "답을 정리하고 있어요"],
};
const LOADING_WORDS: [keyof typeof LOADING_STEPS, RegExp][] = [
  ["help", /병원|약국|응급|의원|아파|다쳤|다치|열이|119|화장실|기저귀/],
  ["food", /식당|밥|카페|먹|음식|맛집|횟집|국수|고기|흑돼지|커피/],
  ["weather", /날씨|비 ?오|비가|바람|더워|추워|내일|모레|주말/],
  ["place", /가고|갈 ?곳|갈 ?만|산책|걷|구경|바다|숲|오름|해변|해수욕|박물관|관광|나들이|어디|데려|추천|다른 ?곳|코스|일정/],
];
const loadingKind = (text: string): keyof typeof LOADING_STEPS =>
  LOADING_WORDS.find(([, re]) => re.test(text))?.[0] ?? "other";
const FAB_BG = `url("${ART.harFace}")`;

const isPhone = () => typeof window !== "undefined" && window.matchMedia("(max-width: 639.98px)").matches;
const reducedMotion = () => typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export function ChatFab({ s }: { s: State }) {
  const label = s.chat_open ? "하르방 도우미 닫기" : "하르방 도우미에게 물어보기";
  const badge = s.unread && !s.chat_open ? Math.min(s.unread, 9) : 0;
  return (
    <>
      <button type="button" id="chatfab" className="chatfab" onClick={toggleChat} style={{ backgroundImage: FAB_BG }}
        aria-label={badge ? `${label}, 새 답 ${badge}개` : label} aria-expanded={s.chat_open} aria-controls="chatwin">
        {badge > 0 && <span className="fab-badge" aria-hidden="true">{badge}</span>}
      </button>
      {!s.chat_open && !s.msgs.length && s.screen === "home" && <div className="fab-hint" aria-hidden="true">하르방에게 물어보세요!</div>}
    </>
  );
}

export function Searching() {
  return (
    <div className="searching" role="status">
      <Svg src={ART.gyul} />
      하르방이 길을 살펴보고 있어요
    </div>
  );
}

// 답변 줄 앞의 말머리를 그림으로 바꿔 한눈에 보이게 한다(화면 읽기 프로그램에는 말머리를 읽어 준다)
const LINE_MARKS: [RegExp, string, string, string][] = [
  [/^조심할 점:\s*/, "⚠️", "warn", "조심할 점"],
  [/^확인할 점:\s*/, "📞", "check", "확인할 점"],
  [/^비 오면:\s*/, "☔", "rain", "비 오면"],
  [/^(응급 상황에는|응급 시에는)/, "🚨", "sos", ""],
];

function AnswerView({ text, phone }: { text: string; phone?: string }) {
  const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
  return (
    <div className="ans">
      {lines.map((ln, i) => {
        const t = /^\*\*(.+?)\*\*\s*[—-]\s*(.+)$/.exec(ln);
        if (i === 0 && t) {
          return (
            <div key={i} className="ans-title">
              <b>{t[1]}</b>
              <span className="ans-tag">{t[2]}</span>
            </div>
          );
        }
        const mk = LINE_MARKS.find(([re]) => re.test(ln));
        if (mk) {
          const [re, icon, cls, label] = mk;
          const body = cls === "sos" ? ln : ln.replace(re, "");
          if (cls === "check") {
            // 확인할 점: 전화번호가 있으면 누르면 바로 전화, 없으면 상자 없이 글자만(눌리는 것처럼 보이지 않게)
            return phone ? (
              <a key={i} className="ans-row check call" href={`tel:${phone}`}>
                <span className="ic" aria-hidden="true">{icon}</span>
                <span className="grow"><span className="sr-only">{label}: </span>{body}</span>
                <span className="go">전화 ›</span>
              </a>
            ) : (
              <div key={i} className="ans-row check plain">
                <span className="ic" aria-hidden="true">{icon}</span>
                <span><span className="sr-only">{label}: </span>{body}</span>
              </div>
            );
          }
          return (
            <div key={i} className={`ans-row ${cls}`}>
              <span className="ic" aria-hidden="true">{icon}</span>
              <span>
                {label && <span className="sr-only">{label}: </span>}
                {cls === "rain" ? <>비 오면 <b>{body}</b></> : body}
              </span>
            </div>
          );
        }
        return <Markdown key={i} text={ln} />;
      })}
    </div>
  );
}

function BotMsg({ m, s, animate }: { m: Msg; s: State; animate?: boolean }) {
  // 새 답은 한 글자씩 쓰지 않고 정리된 상자째 부드럽게 나타난다
  useEffect(() => {
    if (!animate) return;
    const t = window.setTimeout(typingDone, 350);
    return () => window.clearTimeout(t);
  }, [animate]);
  const shown = [...resultNames(s), ...(s.detail_only ? [s.detail_only.place] : [])];
  const order = resultNames(s);
  const places = (m.places ?? []).filter((p) => shown.includes(p));
  const open = (p: string) => {
    showPlace(p);
    closeChat(); // 대화창이 대시보드 자리(휴대폰은 화면 전체)를 덮으므로 닫아서 그 장소의 대시보드를 보여 준다
  };
  return (
    <div className={`bot${animate ? " appear" : ""}`}>
      <Avatar />
      <div className="botb">
        <div className="md">
          <AnswerView text={m.text} phone={m.items?.[0]?.phone} />
        </div>
        {(m.items ?? []).length > 0 && (
          <ul className="mitems">
            {(m.items ?? []).map((it) => (
              <li key={it.name}>
                <div className="mi-name"><b>{it.name}</b><small>{[it.kind, it.phone].filter(Boolean).join(" · ")}</small></div>
                <div className="acts">
                  <LinkButton href={kakaoRouteLink(it.name, it.lat, it.lon)} icon="directions" kind="primary">길안내</LinkButton>
                  {it.phone && <LinkButton href={`tel:${it.phone}`} icon="call">전화</LinkButton>}
                  <button type="button" className="btn btn-secondary" onClick={() => focusItem(it.name, true)} aria-label={`${it.name} 지도에서 보기`}>
                    <Icon name="map" /><span>지도</span>
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
        {places.length > 0 && (
          <div className="mplaces-wrap">
            <p className="mp-cap">추천 후보 · 누르면 지도와 아래에서 자세히 보여요</p>
            <div className="mplaces">
              {places.map((p) => {
                const n = order.indexOf(p) + 1;
                return (
                  <button key={p} type="button" className="mp-btn" onClick={() => open(p)} aria-label={`${p} 자세히 보기`}>
                    {n > 0 && <i className="num" aria-hidden="true">{n}</i>}
                    <span>{p}</span>
                    <span className="chev" aria-hidden="true">›</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Typing({ text }: { text: string }) {
  const steps = LOADING_STEPS[loadingKind(text)];
  return (
    <div className="typing" role="status" aria-live="polite">
      <Avatar />
      <div className="bub">
        <span className="dots" aria-hidden="true"><i /><i /><i /></span>
        <div className="steps">
          {steps.slice(0, 3).map((t, i) => <span key={i} aria-hidden={i > 0 ? true : undefined}>{t}</span>)}
        </div>
      </div>
    </div>
  );
}

export function ChatWindow({ s }: { s: State }) {
  const [text, setText] = useState("");
  const input = useRef<HTMLInputElement>(null);

  // 열리면 입력창으로(휴대폰은 자판이 화면을 가려서 바로 올리지 않는다). Esc 로 닫는다.
  useEffect(() => {
    if (!isPhone()) input.current?.focus();
    const onKey = (e: globalThis.KeyboardEvent) => {
      if (e.key === "Escape") {
        closeChat();
        document.getElementById("chatfab")?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // 새 말이 붙으면 맨 아래(가장 최근 말)로 내린다. 말풍선은 위에서부터 차례로 쌓인다.
  const log = useRef<HTMLDivElement>(null);
  useEffect(() => {
    log.current?.scrollTo({ top: log.current.scrollHeight, behavior: "smooth" });
  }, [s.msgs.length, s.pending, s.typing]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (s.pending || !text.trim()) return;
    go(text, null, true);
    setText("");
  };

  const animate = reducedMotion() ? null : s.typing;
  const placeholder = !s.msgs.length ? "예: 아빠가 휠체어 타요. 바다 보고 싶어요" : "더 물어보세요 (예: 근처 씹기 편한 음식점)";
  const options = [...new Set((s.ask?.options ?? []).map((o) => String(o)))];

  return (
    <section id="chatwin" className="chatwin" role="dialog" aria-label="하르방 도우미 대화창">
      <div className="chathead basalt">
        <div className="chat-head">
          <Avatar />
          <div>
            <b>하르방 도우미</b>
            <small>가고 싶은 곳, 함께 가는 분을 말해 주세요</small>
          </div>
        </div>
        <button type="button" className="tb-btn" onClick={() => { closeChat(); document.getElementById("chatfab")?.focus(); }}>
          <Icon name="close" />
          <span>닫기</span>
        </button>
      </div>
      <div className="chatlog" ref={log}>
        {!s.msgs.length && (
          <div className="chat-empty">
            <h3>누구와 어디로 가세요?</h3>
            <p>{GREETING.replace(/\*\*/g, "")}</p>
            <ul className="ex-list">
              {EXAMPLES.map(([ic, ex]) => (
                <li key={ex}>
                  <button type="button" onClick={() => go(ex, null, true)}>
                    <span className="ic" aria-hidden="true">{ic}</span>
                    <span>{ex}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
        <div className="chatlist" role="log" aria-live="polite" aria-relevant="additions">
          {s.msgs.map((m, i) =>
            m.role === "user" ? (
              <div key={i} className="msg-me"><span className="sr-only">나: </span>{m.text}</div>
            ) : (
              <BotMsg key={i} m={m} s={s} animate={i === animate && !s.pending} />
            ),
          )}
          {s.ask && !s.pending && options.length > 0 && (
            <div className="askopts">
              {options.map((o) => (
                <button key={o} type="button" className="btn btn-primary pill-btn"
                  onClick={() => (o === "내 위치로 찾기" ? locateAndRetry() : go(o, null, true))}>
                  {o === "내 위치로 찾기" && <Icon name="my_location" />}{o}
                </button>
              ))}
            </div>
          )}
          {s.pending && <Typing text={s.pending.text} />}
        </div>
      </div>
      <form className="chatform" onSubmit={submit}>
        <label htmlFor="chat-text" className="sr-only">하르방에게 할 말</label>
        <input id="chat-text" ref={input} type="text" value={text} onChange={(e) => setText(e.target.value)}
          placeholder={placeholder} autoComplete="off" enterKeyHint="send" />
        <button type="submit" className="btn btn-primary send" disabled={!!s.pending || !text.trim()} aria-label="보내기">
          <Icon name="send" />
        </button>
      </form>
    </section>
  );
}
