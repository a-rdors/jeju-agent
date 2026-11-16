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
             "selected": None, "big": False, "food": None, "when": "오늘",
             "location": None, "shown": []}.items():  # location: (위도, 경도). 지도 화면에서 위치 권한 허용 시 채운다
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
    for name, args, res in out["tool_results"]:
        if name == "get_weather" and args.get("when"):
            S.when = args["when"]
        if name == "search_food":  # 최근 결과 하나만 크게 보여준다
            S.food, S.results = res, None
        if name == "recommend_places":
            S.results, S.food = res, None
            S.selected = res["results"][0]["place"]
            S.shown = list(dict.fromkeys(S.shown + [r["place"] for r in res["results"]]))
            if args.get("user_type"):
                S.user_type = args["user_type"]
    S.ask = out["ask"]
    S.chat.append({"role": "assistant", "text": out["text"], "trace": out.get("trace", [])})
    S.history.append({"role": "assistant", "content": out["text"]})


def reset():
    for k in ("history", "chat"):
        S[k] = []
    for k in ("ask", "results", "selected", "food"):
        S[k] = None
    S.shown = []
    S.user_type, S.when = "other", "오늘"


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
if S.food:
    f = S.food
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
                    st.badge("휠체어 진입 확인(2021)", icon=":material/accessible:", color="green")
                for w in it.get("why", []):
                    st.badge(w.split(":")[0], icon=":material/restaurant:", color="blue")
            if it.get("why"):
                st.caption(" · ".join(w.split(": ", 1)[-1] for w in it["why"]) + " (추정)")
            with st.container(horizontal=True):
                st.link_button("길안내", T.kakao_route_link(it["name"], it["lat"], it["lon"]),
                               icon=":material/directions:", type="primary", key=f"food_nav_{i}")
                if it["phone"]:
                    st.link_button(f"전화 {it['phone']}", f"tel:{it['phone']}", icon=":material/call:", key=f"food_tel_{i}")
    with st.expander("전화로 이것만 물어보세요", icon=":material/call:", expanded=bool(f.get("diet_needs"))):
        for q in T.call_questions(S.user_type, f.get("diet_needs")):
            st.markdown(f"- {q}")
    st.caption(f["note"])

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
            st.badge(f"경사 {top['slope_level']}", icon=icon, color=color)
            st.badge(f"약 {top['minutes']}분 · {top['course_m']:,}m", icon=":material/schedule:", color="gray")
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
            others = [r for r in res if r["place"] != top["place"]]
            if others:
                with st.popover("다른 곳 보기", icon=":material/swap_horiz:"):
                    for r in others:
                        if st.button(f"{r['place']} · 경사 {r['slope_level']}", key=f"pick_{r['place']}", width="stretch"):
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
        ["확인한 것", "코스 따라가기", "병원·약국", "주변 식당", "전화 질문"])
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
        else:
            st.caption("특별히 확인할 지점 기록이 없어요.")
    with tab_help:
        help_ = T.find_nearby_help(top["place"])
        for kind, items in help_["help"].items():
            for it in items:
                st.markdown(f"**{kind}** · {it['name']} ({it['km']}km)  \n{it['address']}")
                if it["phone"]:
                    st.link_button(f"전화 {it['phone']}", f"tel:{it['phone']}", icon=":material/call:")
        st.caption(help_["note"])
    with tab_food:
        near = T.check_nearby_places(top["place"], limit=8)
        labels = {"영업 확인": ":green-badge[2025 영업 확인]", "확인 안 됨": ":gray-badge[영업 확인 안 됨]",
                  "폐업 기록": ":red-badge[폐업 기록]"}
        for it in near["items"]:
            wc = " :green-badge[휠체어 진입]" if it["wheelchair_entry"] else ""
            st.markdown(f"**{it['name']}** · {it['category']} · {it['km']}km {labels[it['open_status']]}{wc}")
        st.caption(near["note"])
    with tab_call:
        st.markdown("가기 전에 전화로 이것만 물어보세요.")
        for q in T.call_questions(S.user_type):
            st.markdown(f"- {q}")

    st.caption(f"자료: 제주데이터허브 무장애여행 정보(제주특별자치도, {detail['base_date']} 기준). 현장과 다를 수 있어요.")

if S.chat:
    st.button("처음부터 다시", icon=":material/refresh:", type="tertiary", on_click=reset)
