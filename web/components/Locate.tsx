"use client";
// 지도 왼쪽 '내 위치' 단추(지도 앱처럼). 누르면 지도가 내 자리로 가고, 시작 화면 찾기도 내 근처 기준이 된다.
import { useEffect, useState } from "react";
import { locateMe } from "@/lib/store";
import Icon from "./Icon";

export default function LocateButton({ on }: { on: boolean }) {
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");

  // 안내 말은 잠깐 보였다가 사라진다
  useEffect(() => {
    if (!note) return;
    const t = window.setTimeout(() => setNote(""), 4500);
    return () => window.clearTimeout(t);
  }, [note]);

  const click = async () => {
    if (busy) return;
    setBusy(true);
    setNote("");
    const msg = await locateMe();
    setBusy(false);
    setNote(msg);
  };

  return (
    <>
      <button type="button" className={`locate${on ? " on" : ""}${busy ? " busy" : ""}`} onClick={click}
        aria-label={on ? "내 위치로 지도 다시 옮기기" : "내 위치로 지도 옮기기"} title="내 위치" aria-busy={busy}>
        <Icon name="my_location" />
      </button>
      {note && <p className="locate-note" role="status">{note}</p>}
    </>
  );
}
