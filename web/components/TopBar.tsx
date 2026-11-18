"use client";
// 왼쪽 위: 이름표와 설정 버튼 3개(큰 글씨·패널·처음으로)를 정사각형 하나(2×2)에 담는다. 그 아래에 지도 범례.
// 휴대폰은 같은 상자를 위쪽 한 줄로 펼친다.
import { ART } from "@/lib/art";
import { home, setBig, togglePanel, type State } from "@/lib/store";
import { Svg } from "./bits";
import Icon from "./Icon";

export default function TopBar({ s, legend, hint }: { s: State; legend: [string, string][]; hint: string }) {
  const panelLabel = s.panel_open ? "패널 숨기기" : "패널 보기";
  const canReset = s.screen !== "home" || s.msgs.length > 0;
  return (
    <header className="rail">
      <div className="box basalt">
        <div className="brand" title="제주 같이나들이: 휠체어·유모차·어르신과 함께 가는 제주">
          <Svg src={ART.hareubang} className="mini" />
          <h1>제주 <br />같이나들이</h1>
        </div>
        <button type="button" role="switch" aria-checked={s.big} className="tool" onClick={() => setBig(!s.big)}
          title="큰 글씨">
          <Icon name="format_size" />
          <span className="lbl">큰 글씨</span>
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
          {hint && <p>{hint}</p>}
        </div>
      )}
    </header>
  );
}
