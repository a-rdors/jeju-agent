"""제주 같이나들이 - Streamlit 화면.

실행: .venv\\Scripts\\streamlit run app/main.py --server.address localhost
원칙: 사용자가 가장 편하게. 숫자를 묻지 않고, 결과는 하나를 크게, 바로 행동할 버튼을 붙인다.
"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import agent as A  # noqa: E402
import tools as T  # noqa: E402

st.set_page_config(page_title="제주 같이나들이", page_icon=":material/accessible:", layout="centered")

# ---------- 상태 ----------
S = st.session_state
for k, v in {"history": [], "chat": [], "ask": None, "results": None, "user_type": "other",
             "selected": None, "big": False, "foods": [], "help": None, "when": "오늘",
             "location": None, "shown": [], "itinerary": [], "diet": []}.items():  # location: (위도, 경도). 지도 화면에서 위치 권한 허용 시 채운다
    S.setdefault(k, v)

TYPES = [  # (버튼 글자, 아이콘, 이동 유형, 보낼 문장)
    ("휠체어", ":material/accessible:", "manual_wheelchair", "휠체어 타는 가족과 나들이 갈 곳 추천해 줘"),
    ("유모차", ":material/child_friendly:", "stroller", "유모차 끌고 갈 만한 곳 추천해 줘"),
    ("어르신", ":material/elderly:", "senior", "부모님 모시고 가볍게 다녀올 곳 추천해 줘"),
]
EXAMPLES = ["비 오는 날 실내로 갈 곳", "바다 보면서 천천히 걷고 싶어", "숲길 산책하고 싶어", "근처 해산물 식당"]
STEP_NAMES = {
    "recommend_places": "조건에 맞는 장소 찾기", "get_weather": "날씨 확인",
    "search_food": "들어갈 수 있는 식당 찾기", "get_place_detail": "코스 살펴보기",
    "find_nearby_help": "가까운 병원·약국 찾기", "check_nearby_places": "주변 가게 확인",
    "ask_user": "필요한 것 여쭤보기",
}
SLOPE_BADGE = {"완만한 편": ("green", ":material/check_circle:"), "보통": ("orange", ":material/info:"),
               "가파른 편": ("red", ":material/warning:"), "기록 없음": ("gray", ":material/help:")}

# 큰 글씨: 테마는 실행 중 바꿀 수 없어서 이 기능만 CSS로 처리(사용자 요청 기능)
if S.big:
    st.html("<style>html{font-size:125%;}</style>")


def send(text, user_type=None):
    """사용자 말을 처리한다. 버튼으로 이동 유형을 고르면 AI 없이 바로 추천(빠르고 항상 같은 결과)."""
    if user_type:
        S.user_type = user_type
    S.chat.append({"role": "user", "text": text, "trace": []})
    S.history.append({"role": "user", "content": text})
    S.ask = None
    with st.spinner("알맞은 곳을 찾고 있어요..."):
        if user_type:
            out = A.rule_mode(text, user_type)
        else:
            known = S.user_type if S.user_type != "other" else None
            try:
                out = (A.run(S.history, known, S.selected, S.location, S.shown) if A.available()
                       else A.rule_mode(text, known))
            except Exception:
                out = A.rule_mode(text, known)
                out["text"] = "(AI 연결이 안 돼서 기본 모드로 찾았어요) " + out["text"]
    # 이번 질문에서 나온 결과는 전부 보여주고(예: 횟집과 카페를 한 번에 찾은 경우), 다음 질문에서 새로 바꾼다
    turn_foods, turn_places, turn_plan, turn_help = [], None, False, None
    for name, args, res in out["tool_results"]:
        if name == "get_weather" and args.get("when"):
            S.when = args["when"]
        if name == "search_food":
            turn_foods.append(res)
            S.diet = args.get("diet_needs") or S.diet
        if name == "plan_outing" and res.get("stops"):  # 일정 제안: 일정 칸을 채운다
            S.itinerary, turn_plan = res["stops"], True
            S.diet = args.get("diet_needs") or S.diet
        if name == "find_nearby_help" and "help" in res:
            turn_help = res
        if name == "recommend_places":
            turn_places = res
            S.selected = res["results"][0]["place"]
            S.shown = list(dict.fromkeys(S.shown + [r["place"] for r in res["results"]]))
            if args.get("user_type"):
                S.user_type = args["user_type"]
    if turn_foods or turn_places or turn_plan:
        S.foods, S.results = turn_foods, turn_places
    if turn_foods or turn_places or turn_plan or turn_help:
        S.help = turn_help
    S.ask = out["ask"]
    S.chat.append({"role": "assistant", "text": out["text"], "trace": out.get("trace", [])})
    S.history.append({"role": "assistant", "content": out["text"]})


def reset():
    for k in ("history", "chat"):
        S[k] = []
    for k in ("ask", "results", "selected"):
        S[k] = None
    S.shown, S.itinerary, S.diet, S.foods, S.help = [], [], [], [], None
    S.user_type, S.when = "other", "오늘"


def add_stop(stop):
    """'+ 일정' 버튼: 같은 곳을 두 번 담지 않는다."""
    if stop and all(x["name"] != stop["name"] for x in S.itinerary):
        S.itinerary.append(stop)


def remove_stop(name):
    S.itinerary = [x for x in S.itinerary if x["name"] != name]


# ---------- 머리말 ----------
with st.container(horizontal=True, vertical_alignment="center"):
    st.title(":material/accessible_forward: 제주 같이나들이", width="stretch")
    st.toggle("큰 글씨", key="big", help="글자를 크게 키워요")
st.caption("휠체어·유모차·어르신과 함께 갈 수 있는 제주 나들이를, 공공데이터 근거로 찾아드려요.")

# ---------- 첫 화면 ----------
if not S.chat:
    st.subheader("누구와 함께 가세요?")
    with st.container(horizontal=True):
        for label, icon, ut, text in TYPES:
            if st.button(label, icon=icon, type="primary", width="stretch", key=f"type_{ut}"):
                send(text, ut)
                st.rerun()
    st.markdown("**이렇게 말해도 돼요**")
    with st.container(horizontal=True):
        for ex in EXAMPLES:
            if st.button(ex, type="secondary", key=f"ex_{ex}"):
                send(ex)
                st.rerun()

# ---------- 대화 ----------
for m in S.chat[-6:]:
    icon = ":material/person:" if m["role"] == "user" else ":material/accessible_forward:"
    with st.chat_message(m["role"], avatar=icon):
        if m["trace"]:
            with st.status("확인한 것", type="compact", state="complete"):
                for t in m["trace"]:
                    with st.status(STEP_NAMES.get(t["tool"], t["tool"]), type="step", state="complete"):
                        st.caption(", ".join(f"{k}: {v}" for k, v in t["args"].items() if v not in (None, "", False)))
        st.markdown(m["text"])

if S.ask:
    with st.container(horizontal=True):
        for opt in S.ask["options"]:
            if st.button(opt, type="primary", key=f"opt_{opt}"):
                send(opt)
                st.rerun()

prompt = st.chat_input("예: 아빠가 휠체어 타세요. 바다 보러 가고 싶어요", submit_mode="disable")
if prompt:
    send(prompt)
    st.rerun()

# ---------- 식당 결과 ----------
for fi, f in enumerate(S.foods):
    cond = " · ".join(f.get("diet_labels") or [])
    st.subheader(f"{f['around']} 근처 {cond or (f['food_kind'] or '식당')}", divider="gray")
    if f.get("anchor_not_found"):
        st.info(f["note"], icon=":material/info:")
    elif not f["items"]:
        st.info("조건에 맞는 식당을 찾지 못했어요. 조건을 줄이거나 동네를 바꿔 보세요.", icon=":material/info:")
    for i, it in enumerate(f["items"]):
        with st.container(border=True):
            st.markdown(f"**{it['name']}**  \n{it['food_type']}" + (f" · {it['km']}km" if it["km"] is not None else ""))
            with st.container(horizontal=True):
                if it["wheelchair_entry"]:
                    st.badge("휠체어 진입 확인", icon=":material/accessible:", color="green", help=it["access_info"])
                fn = it.get("floor_note", "")
                if fn:
                    st.badge(fn, icon=":material/stairs:",
                             color="green" if fn == "1층" else ("gray" if fn == "층 정보 없음" else "orange"))
                if it.get("baby_chair"):
                    st.badge("아기 의자 있음", icon=":material/child_care:", color="green")
                for w in it.get("why", []):
                    st.badge(w.split(":")[0], icon=":material/restaurant:", color="blue")
            if it.get("why"):
                st.caption(" · ".join(w.split(": ", 1)[-1] for w in it["why"]) + " (추정)")
            with st.container(horizontal=True):
                st.link_button("길안내", T.kakao_route_link(it["name"], it["lat"], it["lon"]),
                               icon=":material/directions:", type="primary", key=f"food_nav_{fi}_{i}")
                if it["phone"]:
                    st.link_button(f"전화 {it['phone']}", f"tel:{it['phone']}", icon=":material/call:", key=f"food_tel_{fi}_{i}")
                if it.get("place_url"):
                    st.link_button("카카오맵 정보", it["place_url"], icon=":material/info:", key=f"food_info_{fi}_{i}")
                st.button("+ 일정", type="tertiary", key=f"food_add_{fi}_{i}", on_click=add_stop, args=(T.food_stop(it),),
                          help="하루 일정에 담기")
    st.caption(f["note"])
if S.foods:
    with st.expander("전화로 이것만 물어보세요", icon=":material/call:", expanded=bool(S.diet)):
        for q in T.call_questions(S.user_type, S.diet):
            st.markdown(f"- {q}")

# ---------- 근처 약국·병원·화장실(대화로 물었을 때) ----------
if S.help:
    st.subheader(f"{S.help['place']} 근처 약국·병원·화장실", divider="gray")
    icons = {"약국": ":material/local_pharmacy:", "병·의원": ":material/local_hospital:", "응급실": ":material/emergency:",
             "장애인 화장실": ":material/wc:", "기저귀 교환대": ":material/baby_changing_station:"}
    for kind, items in S.help["help"].items():
        for j, it in enumerate(items):
            with st.container(border=True, horizontal=True, vertical_alignment="center"):
                st.markdown(f"**{kind}** · {it['name']} ({it['km']}km)  \n{it.get('address', '')}", width="stretch")
                if it.get("lat"):
                    st.link_button("길안내", T.kakao_route_link(it["name"], it["lat"], it["lon"]),
                                   icon=icons.get(kind, ":material/directions:"), key=f"help_nav_{kind}_{j}")
                if it.get("phone"):
                    st.link_button("전화", f"tel:{it['phone']}", icon=":material/call:", key=f"help_tel_{kind}_{j}")
    st.caption(S.help["note"])

# ---------- 추천 장소 ----------
if S.results:
    res = S.results["results"]
    top = next((r for r in res if r["place"] == S.selected), res[0])
    color, icon = SLOPE_BADGE.get(top["slope_level"], ("gray", ":material/help:"))

    st.subheader("추천 장소", divider="gray")
    with st.container(border=True):
        v_icon = {"green": ":material/check_circle:", "orange": ":material/group:", "gray": ":material/help:"}
        st.badge(top["verdict"], icon=v_icon.get(top["verdict_color"], ":material/help:"), color=top["verdict_color"])
        st.markdown(f"### {top['place']}")
        st.caption(f"{top['where']} · {top['verdict_reason']}")
        with st.container(horizontal=True):
            if top["minutes"]:  # 코스(제주도 조사) 장소
                st.badge(f"경사 {top['slope_level']}", icon=icon, color=color)
                st.badge(f"약 {top['minutes']}분 · {top['course_m']:,}m", icon=":material/schedule:", color="gray")
            else:  # 시설(관광공사) 장소
                st.badge("시설 방문", icon=":material/museum:", color="gray")
            if top["distance_km"] is not None:
                st.badge(f"{top['distance_km']}km 거리", icon=":material/place:", color="gray")
            if top["accessible_toilet"]:
                st.badge("장애인 화장실", icon=":material/wc:", color="green")
            if top["accessible_parking"] == "yes":
                st.badge("장애인 주차", icon=":material/local_parking:", color="green")
            if top["companion_advised"]:
                st.badge("동행인과 함께 권장", icon=":material/group:", color="orange")
        st.markdown(f"**{top['slope_say']}**")
        for g in top["good_points"]:
            st.markdown(f":material/check: {g}")
        for w in top["watch_out"]:
            st.markdown(f":material/warning: {w}")
        with st.container(horizontal=True):
            st.link_button("카카오맵 길안내", T.kakao_route_link(top["place"], top["lat"], top["lon"]),
                           icon=":material/directions:", type="primary")
            st.button("+ 일정", type="tertiary", key="place_add", on_click=add_stop,
                      args=(T.place_stop(top["place"], S.user_type),), help="하루 일정에 담기")
            others = [r for r in res if r["place"] != top["place"]]
            if others:
                with st.popover("다른 곳 보기", icon=":material/swap_horiz:"):
                    for r in others:
                        if st.button(f"{r['place']} · {r['verdict']}", key=f"pick_{r['place']}", width="stretch"):
                            S.selected = r["place"]
                            st.rerun()

    wx = T.get_weather(place=top["place"], when=S.when)
    if wx.get("available"):
        line = f"{wx['date']} 날씨: 비 올 확률 {wx['rain_chance']}% · 바람 {wx['wind_ms']:.0f}m/s · {wx['temp']} (Open-Meteo 예보)"
        if wx["tips"]:
            st.warning("  \n".join(wx["tips"]), icon=":material/umbrella:", title="날씨 주의")
        st.caption(line)
    else:
        st.caption(wx["note"])

    detail = T.get_place_detail(top["place"], S.user_type)
    tab_check, tab_course, tab_help, tab_food, tab_call = st.tabs(
        ["확인한 것", "코스·위치", "병원·약국·화장실", "주변 식당", "전화 질문"])
    with tab_check:
        for c in detail["checks"]:
            mark = ":green-badge[확인됨]" if c["known"] else ":gray-badge[확인 안 됨]"
            st.markdown(f"**{c['item']}** · {c['status']} {mark}")
        st.caption(detail["source"])
    with tab_course:
        pts = pd.DataFrame(detail["all_points"])
        if not pts.empty:
            pts["color"] = ["#C0392B" if f else "#0B6B55" for f in pts["flags"]]
            st.map(pts, latitude="lat", longitude="lon", color="color", size=6, height=320,
                   alt=f"{top['place']} 코스 지도. 빨간 점은 주의 지점, 초록 점은 일반 지점")
            st.caption("빨간 점: 확인할 지점 · 초록 점: 일반 지점")
        if detail["key_points"]:
            for s_ in detail["key_points"]:
                with st.container(border=True):
                    st.markdown(f"**출발 후 약 {s_['at_m']}m** · {s_['label']}")
                    st.markdown(" ".join(f":gray-badge[{f}]" for f in s_["flags"]))
        elif detail.get("data_kind") == "시설(관광공사)":
            st.caption("시설 입구 기준 정보예요. 코스를 따라 경사를 잰 자료는 아니에요.")
        else:
            st.caption("특별히 확인할 지점 기록이 없어요.")
        if detail.get("toilets_near"):
            st.markdown("**가까운 장애인 화장실**")
            for t_ in detail["toilets_near"]:
                extra = " · 기저귀 교환대" if t_["diaper"] else ""
                st.markdown(f"- {t_['name']} ({int(t_['km'] * 1000)}m){extra} · {t_['open']}")
    with tab_help:
        help_ = T.find_nearby_help(top["place"])
        for kind, items in help_["help"].items():
            for it in items:
                st.markdown(f"**{kind}** · {it['name']} ({it['km']}km)  \n{it.get('address', '')}")
                if it["phone"]:
                    st.link_button(f"전화 {it['phone']}", f"tel:{it['phone']}", icon=":material/call:")
        st.caption(help_["note"])
    with tab_food:
        near = T.search_food(place=top["place"], limit=6,
                             prefer_wheelchair=S.user_type in ("manual_wheelchair", "electric_wheelchair"))
        for it in near["items"]:
            wc = " :green-badge[휠체어 진입 확인]" if it["wheelchair_entry"] else ""
            tel = f" · {it['phone']}" if it["phone"] else ""
            st.markdown(f"**{it['name']}** · {it['food_type']} · {it['km']}km{wc}{tel}")
        st.caption("음식점 정보: 2025 상가 자료, 휠체어 배지: 2021 무장애 조사·한국관광공사, 전화번호: 카카오")
    with tab_call:
        st.markdown("가기 전에 전화로 이것만 물어보세요.")
        for q in T.call_questions(S.user_type):
            st.markdown(f"- {q}")

    st.caption(f"자료: {detail['source']} · 기준 {detail['base_date']}. 현장과 다를 수 있어요.")

# ---------- 오늘 일정(담았을 때만 보임) ----------
if S.itinerary:
    st.subheader(f"오늘 일정 ({len(S.itinerary)}곳)", divider="gray")
    legs = T.itinerary_legs(S.itinerary)
    for i, stop in enumerate(S.itinerary):
        if i:
            st.caption(f"↓ 약 {legs[i - 1]['km']}km (직선)")
        with st.container(border=True, horizontal=True, vertical_alignment="center"):
            label = stop["verdict"] if stop["kind"] == "place" else stop.get("food_type", "")
            st.markdown(f"**{i + 1}. {stop['name']}**  \n{label}", width="stretch")
            st.link_button("길안내", T.kakao_route_link(stop["name"], stop["lat"], stop["lon"]),
                           icon=":material/directions:", key=f"it_nav_{i}")
            st.button("빼기", type="tertiary", key=f"it_del_{i}", on_click=remove_stop, args=(stop["name"],))
    html_sheet = T.itinerary_html(S.itinerary, S.user_type, S.diet, S.when)
    st.download_button("일정표 내려받기", data=html_sheet.encode("utf-8"), file_name="같이나들이_일정표.html",
                       mime="text/html", icon=":material/print:", type="primary",
                       help="내려받은 파일을 열어 인쇄하거나 PDF로 저장하세요")
    st.caption("일정표: 들르는 순서·거리, 장소별 확인표, 가까운 장애인 화장실, 급할 때 연락처, 전화로 확인할 것")

if S.chat:
    st.button("처음부터 다시", icon=":material/refresh:", type="tertiary", on_click=reset)
