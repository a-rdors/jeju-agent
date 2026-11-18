"use client";
// 판정 근거 펼치기: 판정 상자 안의 "근거 보기"를 누르면 그 판정 뒤에 있는 공공데이터 기록 원문을 보여 준다.
// 자료 모양은 app/tools.py 의 evidence 필드(.omc/plans/evidence.md)를 따른다.
import { useState } from "react";
import type { Evidence, EvidenceItem } from "@/lib/api";
import { Verdict } from "./bits";
import Icon from "./Icon";

// 판정을 어렵게 만드는 표시는 빨강, 도움이 되는 표시는 초록
const GOOD_FLAGS = new Set(["장애인 화장실", "장애인 주차"]);

/** 판정 상자 + (근거가 있으면) 근거 보기 단추와 펼친 목록 */
export function VerdictWithEvidence({
  color, label, reason, evidence,
}: { color: string; label: string; reason: string; evidence?: Evidence | null }) {
  const [open, setOpen] = useState(false);
  const has = !!evidence && evidence.items.length > 0;
  const btn = has ? (
    <button type="button" className="ev-toggle" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
      {open ? "근거 닫기" : evidence!.kind === "course" ? `근거 보기 · 조사 지점 ${evidence!.items.length}곳` : "근거 보기"}
    </button>
  ) : null;
  return (
    <>
      <Verdict color={color} label={label} reason={reason} extra={btn} />
      {has && open && <EvidenceList ev={evidence!} />}
    </>
  );
}

export function EvidenceList({ ev }: { ev: Evidence }) {
  const [all, setAll] = useState(false);
  // 코스는 판정에 쓴 지점만 먼저, 시설은 항목이 적어 전부 보여 준다
  const first = ev.kind === "course" ? ev.items.filter((i) => i.used) : ev.items;
  const rest = ev.kind === "course" ? ev.items.filter((i) => !i.used) : [];
  const shown = all || first.length === 0 ? ev.items : first;
  const left = all || first.length === 0 ? 0 : rest.length;
  return (
    <div className="evidence" role="region" aria-label="판정 근거">
      <p className="ev-sum">{ev.summary}</p>
      <ul className="ev-list">
        {shown.map((it, i) => <Item key={`${it.label}-${i}`} it={it} />)}
      </ul>
      {left > 0 && (
        <button type="button" className="ev-more" onClick={() => setAll(true)}>
          <span>나머지 {left}곳 더 보기</span>
          <Icon name="expand_more" />
        </button>
      )}
      <p className="src">
        출처: {ev.kind === "course"
          ? `${ev.source}(${ev.survey}, ${ev.base_date} 기준)`
          : `${ev.source}(수시 갱신)`}. 조사 원문 그대로라 휠체어 기준 문구가 있을 수 있어요.
      </p>
    </div>
  );
}

function Item({ it }: { it: EvidenceItem }) {
  // 원문은 "지점 이름 | 내용" 꼴이 많다. 이름은 굵게 따로 보여 주고 내용만 남긴다.
  const body = it.text.startsWith(`${it.label} | `) ? it.text.slice(it.label.length + 3) : it.text;
  const where = it.at_m != null ? `출발 후 ${it.at_m.toLocaleString("ko-KR")}m` : it.on_route === false ? "코스 옆" : "";
  return (
    <li className={it.used ? "used" : ""}>
      <div className="ev-head">
        <b>{it.label}</b>
        {where && <small>{where}</small>}
        {it.used && <span className="tag">판정에 씀</span>}
      </div>
      {body && body !== it.label && <p>{body}</p>}
      {it.flags.length > 0 && (
        <div className="tags">
          {it.flags.map((f) => <span key={f} className={`tag ${GOOD_FLAGS.has(f) ? "wc" : "red"}`}>{f}</span>)}
        </div>
      )}
    </li>
  );
}
