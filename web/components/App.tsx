"use client";
// 한 화면 앱: 지도(화면 전체) 위에 상단 바 · 대시보드 · 하르방 버튼 · 대화창이 떠 있다. (main.py 그리기 순서)
import { useEffect, useMemo } from "react";
import KakaoMap from "@/components/KakaoMap";
import { buildMapData, legendItems } from "@/lib/mapData";
import type { MapData } from "@/lib/types";
import { isError, urls } from "@/lib/api";
import type { Config, Detail, Food, Help, PlaceDot } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { focusItem, lookPlace, showPlace, topPlace, useStore, type State } from "@/lib/store";
import { ChatFab, ChatWindow, Searching } from "./Chat";
import Dashboard from "./Dashboard";
import TopBar from "./TopBar";

/** 지도 쓰는 법 한 줄(패널 대신 범례 아래에 둔다) */
function mapHint(d: MapData): string {
  const kinds = new Set(d.marks.map((m) => m.kind));
  if (kinds.has("place") && d.marks.filter((m) => m.kind === "place").length > 1) return "패널의 번호 버튼을 누르면 그곳으로 바뀌어요";
  return "";
}

/** main.py map_data() 와 같은 갈래. 필요한 도구 결과는 저장된 것을 다시 쓴다. */
function useMapData(s: State) {
  const top = topPlace(s);
  const onResult = s.screen === "result" && !!top;
  const ownFood = top && s.food && s.food.around === top.place ? s.food : null;
  const det = useApi<Detail | { error: string }>(onResult && top ? urls.detail(top.place, s.user_type) : null);
  const food = useApi<Food>(onResult && top && s.tab === "식당" && !ownFood
    ? urls.food(top.place, s.user_type.includes("wheelchair")) : null);
  const help = useApi<Help>(onResult && top && s.tab === "병원·약국" ? urls.help(top.place) : null);
  const places = useApi<PlaceDot[]>(urls.places);

  return useMemo(() => {
    if (onResult && top) {
      return buildMapData({
        wheel: s.user_type.includes("wheelchair"),
        focus: s.focus,
        results: s.results?.results ?? [],
        selected: top.place,
        placeInfo: places.data ?? [],
        detail: det.data && !isError(det.data) ? det.data : undefined,
        food: s.tab === "식당" ? (ownFood ?? food.data) : undefined,
        help: s.tab === "병원·약국" && help.data && !isError(help.data) ? help.data : undefined,
      });
    }
    if (s.screen === "food" && s.food) return buildMapData({ food: s.food, wheel: s.user_type.includes("wheelchair"), focus: s.focus });
    if (s.screen === "answer" && (s.detail_only || s.help_only)) {
      return buildMapData({ detail: s.detail_only ?? undefined, help: s.help_only ?? undefined, wheel: s.user_type.includes("wheelchair"), focus: s.focus });
    }
    return buildMapData({ allPlaces: places.data ?? [] });
  }, [onResult, top, s.results, s.tab, s.screen, s.food, s.detail_only, s.help_only, det.data, ownFood, food.data,
    help.data, places.data, s.user_type, s.focus]);
}

export default function App() {
  const s = useStore();
  const config = useApi<Config>(urls.config);
  const mapData = useMapData(s);
  // 첫 화면(나들이 장소 점만 있을 때)은 범례 상자를 두지 않는다
  const legend = useMemo(() => (mapData.marks.some((m) => m.kind !== "dot") ? legendItems(mapData) : []), [mapData]);

  // 큰 글씨: 글자 기준 크기를 125%로
  useEffect(() => {
    document.documentElement.classList.toggle("big", s.big);
  }, [s.big]);

  const cls = [
    "app",
    s.chat_open ? "chat-open" : "",
    s.panel_open ? "panel-open" : "panel-closed",
    s.sheet === "full" ? "sheet-full" : "",
  ].join(" ");

  return (
    <div className={cls}>
      {(config.data || config.error) ? (
        <KakaoMap
          kakaoKey={config.data?.kakao_js_key ?? ""}
          data={mapData}
          panelOpen={s.panel_open}
          chatOpen={s.chat_open}
          onPick={showPlace}
          onLook={lookPlace}
          onFocus={focusItem}
          focus={s.focus}
          view={s.view}
        />
      ) : (
        <div className="map-wait" aria-hidden="true" />
      )}
      <TopBar s={s} legend={legend} hint={mapHint(mapData)} />
      <Dashboard s={s} userTypes={config.data?.user_types} />
      <ChatFab s={s} />
      {s.pending && <Searching />}
      {s.chat_open && <ChatWindow s={s} />}
    </div>
  );
}
