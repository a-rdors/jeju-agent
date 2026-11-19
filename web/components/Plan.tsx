"use client";
// '내 일정': 카드의 '+ 일정' 단추로 담고, 패널에서 순서를 바꾸거나 빼고, 한 장짜리 일정표로 내려받는다.
// 로그인 없이 이 브라우저에만 저장한다(lib/plan.ts).
import { useState } from "react";
import { api } from "@/lib/api";
import { VERDICT_HEX, FOOD_HEX } from "@/lib/mapData";
import {
  PLAN_MAX, addToPlan, clearPlan, inPlan, kmBetween, movePlan, removeFromPlan, usePlan, type PlanItem,
} from "@/lib/plan";
import { closePlan, focusItem, lookPlace, type State } from "@/lib/store";
import { Info, Shop, Src } from "./bits";
import Icon from "./Icon";

/** 카드에 붙는 '+ 일정' 단추. 담겨 있으면 '일정에 있음'(다시 누르면 뺀다) */
export function PlanButton({ item }: { item: PlanItem }) {
  const list = usePlan();
  const on = inPlan(list, item.name);
  const full = !on && list.length >= PLAN_MAX;
  return (
    <button type="button" className={`btn btn-secondary plan-btn${on ? " on" : ""}`} aria-pressed={on} disabled={full}
      onClick={() => (on ? removeFromPlan(item.name) : addToPlan(item))}
      aria-label={on ? `${item.name} 내 일정에서 빼기` : full ? `내 일정이 가득 찼어요(${PLAN_MAX}곳)` : `${item.name} 내 일정에 담기`}
      title={full ? `내 일정은 ${PLAN_MAX}곳까지 담을 수 있어요` : undefined}>
      <Icon name={on ? "check" : "add"} /><span>일정</span>
    </button>
  );
}

/** 한 장짜리 일정표(HTML)를 파일로 내려받는다. 브라우저로 열어 인쇄하거나 PDF로 저장한다 */
function saveHtml(html: string) {
  const url = URL.createObjectURL(new Blob([html], { type: "text/html;charset=utf-8" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = "제주_같이나들이_내일정.html";
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function PanelPlan({ s }: { s: State }) {
  const list = usePlan();
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");

  const download = async () => {
    setBusy(true);
    setNote("");
    try {
      const r = await api.itinerary({ items: list, user_type: s.user_type, when: s.when });
      if (r.html) saveHtml(r.html);
      else setNote("일정표를 만들지 못했어요. 잠시 뒤 다시 눌러 주세요.");
    } catch {
      setNote("일정표를 만들지 못했어요. 잠시 뒤 다시 눌러 주세요.");
    } finally {
      setBusy(false);
    }
  };

  const clear = () => {
    if (window.confirm(`내 일정 ${list.length}곳을 모두 뺄까요?`)) clearPlan();
  };

  return (
    <>
      <button type="button" className="btn btn-tertiary back" onClick={closePlan}>
        <Icon name="arrow_back" />
        <span>돌아가기</span>
      </button>
      <h2 className="sect">내 일정 {list.length}곳</h2>
      {!list.length ? (
        <Info>아직 담은 곳이 없어요. 추천 결과나 식당 카드의 &lsquo;+ 일정&rsquo;을 눌러 담아 보세요.</Info>
      ) : (
        <>
          <ol className="plan-list">
            {list.map((it, i) => {
              const place = it.kind === "place";
              const color = place ? VERDICT_HEX[it.verdict_color ?? ""] ?? VERDICT_HEX.gray : FOOD_HEX;
              const meta = place ? [it.verdict, it.where].filter(Boolean).join(" · ") : [it.food_type, it.address].filter(Boolean).join(" · ");
              return (
                <li key={it.name}>
                  {i > 0 && (
                    <p className="plan-leg">
                      <Icon name="arrow_downward" />
                      <span>약 {kmBetween(list[i - 1], it)}km (직선)</span>
                    </p>
                  )}
                  <div className={`card plan-card${s.focus === it.name ? " focus" : ""}`}>
                    <div className="plan-row">
                      <i className="plan-no" style={{ background: color }} aria-hidden="true">{i + 1}</i>
                      <Shop name={it.name} meta={meta} tags={[]} />
                      <div className="plan-move">
                        <button type="button" className="icon-btn" onClick={() => movePlan(i, -1)} disabled={i === 0}
                          aria-label={`${it.name} 앞으로`}><Icon name="arrow_upward" /></button>
                        <button type="button" className="icon-btn" onClick={() => movePlan(i, 1)} disabled={i === list.length - 1}
                          aria-label={`${it.name} 뒤로`}><Icon name="arrow_downward" /></button>
                      </div>
                    </div>
                    <div className="acts">
                      {place && (
                        <button type="button" className="btn btn-secondary" onClick={() => lookPlace(it.name)}>
                          <Icon name="info" /><span>자세히</span>
                        </button>
                      )}
                      <button type="button" className="btn btn-secondary" onClick={() => focusItem(it.name)} aria-label={`${it.name} 지도에서 보기`}>
                        <Icon name="map" /><span>지도</span>
                      </button>
                      <button type="button" className="btn btn-secondary" onClick={() => removeFromPlan(it.name)} aria-label={`${it.name} 빼기`}>
                        <Icon name="delete" /><span>빼기</span>
                      </button>
                    </div>
                  </div>
                </li>
              );
            })}
          </ol>
          <div className="acts plan-foot">
            <button type="button" className="btn btn-primary" onClick={download} disabled={busy} aria-busy={busy}>
              <Icon name="download" /><span>{busy ? "만드는 중…" : "일정표 내려받기"}</span>
            </button>
          </div>
          {note && <p className="plan-note" role="status">{note}</p>}
          <button type="button" className="btn btn-tertiary" onClick={clear}>모두 빼기</button>
          <Src>
            이 브라우저에만 저장돼요. 다른 기기에서 보거나 오래 두려면 일정표를 내려받아 두세요.
            거리는 직선거리라 실제 이동은 길안내로 확인해 주세요.
          </Src>
        </>
      )}
    </>
  );
}
