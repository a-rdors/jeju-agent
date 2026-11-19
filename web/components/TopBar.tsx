"use client";
// 왼쪽 위: 이름표와 버튼 4개(큰 글씨·내 일정·패널·처음으로)를 흰색 한 줄 막대에 담는다. 그 아래에 지도 범례.
// 휴대폰은 같은 막대를 화면 위쪽 폭에 맞춘다.
import { ART } from "@/lib/art";
import { usePlan } from "@/lib/plan";
import { home, setBig, togglePanel, togglePlan, type State } from "@/lib/store";
import { Svg } from "./bits";
import Icon from "./Icon";

export default function TopBar({ s, legend, hint }: { s: State; legend: [string, string][]; hint: string }) {
  const panelLabel = s.panel_open ? "패널 숨기기" : "패널 보기";
  const canReset = s.screen !== "home" || s.msgs.length > 0;
  const plan = usePlan();
  return (
    <header className="rail">
      <div className="box">
        <div className="brand" title="제주 같이나들이: 휠체어·유모차·어르신과 함께 가는 제주">
          <Svg src={ART.harFace} className="mini" />
          <div className="brand-txt">
            <h1>제주 같이나들이</h1>
            <p className="brand-sub">휠체어·유모차·어르신과 함께 가는 제주</p>
          </div>
        </div>
        <span className="box-sep" aria-hidden="true" />
        <button type="button" role="switch" aria-checked={s.big} className="tool" onClick={() => setBig(!s.big)}
          title="큰 글씨">
          <Icon name="format_size" />
          <span className="lbl">큰 글씨</span>
        </button>
        <button type="button" className="tool" onClick={togglePlan} aria-pressed={s.screen === "plan"}
          aria-label={`내 일정 ${plan.length}곳`} title="내 일정">
          <Icon name="event_note" />
          <span className="lbl">내 일정</span>
          {plan.length > 0 && <span className="tool-badge" aria-hidden="true">{plan.length}</span>}
        </button>
        <button type="button" className="tool" onClick={togglePanel} aria-label={panelLabel} title={panelLabel}>
          <Icon name={s.panel_open ? "right_panel_close" : "right_panel_open"} />
          <span className="lbl">{s.panel_open ? "패널 숨김" : "패널 보기"}</span>
        </button>
        <button type="button" className="tool" onClick={home} disabled={!canReset} aria-label="처음으로" title="처음으로">
          <Icon name="home" />
          <span className="lbl">처음으로</span>
        </button>
      </div>
      {legend.length > 0 && (
        <div className="legend" aria-label="지도 범례">
          <ul>
            {legend.map(([label, color]) => (
              <li key={label}><i style={{ background: color }} aria-hidden="true" />{label}</li>
            ))}
          </ul>
          {hint && (() => {
            // "넓은 화면 문구||휴대폰 문구" 로 주면 화면 폭에 맞는 쪽만 보인다
            const [wide, phone] = hint.split("||");
            return phone
              ? <p><span className="only-wide">{wide}</span><span className="only-phone">{phone}</span></p>
              : <p>{wide}</p>;
          })()}
        </div>
      )}
    </header>
  );
}
