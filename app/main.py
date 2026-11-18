"""제주 같이나들이 - Streamlit 화면.

실행: .venv\\Scripts\\streamlit run app/main.py --server.address localhost

화면 구성(한 화면 안에서 바뀐다. 페이지 이동·로딩 화면 없음)
  - 바탕: 제주도만 보이는 카카오맵(화면 전체)
  - 왼쪽 위: 상단 바(이름·조건·큰 글씨·패널 숨기기·처음으로)
  - 오른쪽: 대시보드  시작(누구와) / 결과(한눈에·코스·식당·병원·약국·질문지) / 식당 결과 / 장소·병원 답
  - 오른쪽 아래: 감귤 하르방 버튼 -> 누르면 대화창. 대답은 한 글자씩 나오고, 말한 장소는 지도에 바로 뜬다.
좁은 화면(640px 미만)은 대시보드가 아래 시트, 대화창은 화면 전체.
"""
import sys
import time
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import agent as A  # noqa: E402
import map_view as M  # noqa: E402
import tools as T  # noqa: E402
import ui as U  # noqa: E402

st.set_page_config(page_title="제주 같이나들이", page_icon=":material/accessible:", layout="wide",
                   initial_sidebar_state="collapsed")

# ---------- 상태 ----------
S = st.session_state
DEFAULTS = {"history": [], "msgs": [], "ask": None, "results": None, "user_type": "other", "selected": None,
            "big": False, "food": None, "when": "오늘", "shown": [], "screen": "home", "tab": "한눈에",
            "pending": None, "detail_only": None, "help_only": None,
            "chat_open": False, "panel_open": True, "unread": 0, "typing": None,
            "foods": [], "itinerary": [], "diet": [],
            "location": None}  # location: (위도, 경도). 위치 권한을 받으면 채운다
KEEP = {"big", "panel_open"}  # 처음으로 가도 그대로 둘 설정
for k, v in DEFAULTS.items():
    S.setdefault(k, v)

TYPES = [  # (버튼 글자, 아이콘, 이동 유형, 보낼 문장, 설명, 아이콘 배경)
    ("휠체어와 함께", "wheel", "manual_wheelchair", "휠체어 타는 가족과 나들이 갈 곳 추천해 줘",
     "경사·턱·장애인 화장실을 먼저 봐요", "#E3F1E7"),
    ("유모차와 함께", "stroller", "stroller", "유모차 끌고 갈 만한 곳 추천해 줘", "계단 없는 길, 쉬어 갈 곳을 봐요", "#FDE9D6"),
    ("어르신과 함께", "senior", "senior", "부모님 모시고 가볍게 다녀올 곳 추천해 줘", "짧고 완만한 길, 앉을 곳을 봐요", "#E2EDF7"),
    ("임산부와 함께", "pregnant", "pregnant", "임산부와 무리 없이 다녀올 곳 추천해 줘", "짧은 코스, 화장실·산부인과를 봐요", "#F6E4EE"),
]
EXAMPLES = ["휠체어 타는 아빠랑 바다 보러 가고 싶어", "비 오는 날 아기랑 실내로 갈 곳",
            "할머니가 이가 안 좋으셔서 제주시에서 밥 먹을 곳", "임산부랑 서귀포에서 반나절 일정 짜줘"]
GREETING = ("안녕하세요, 하르방 도우미예요. 누구와 어디로 가고 싶은지 편하게 말해 주세요. "
            "찾은 곳은 지도에 바로 보여 드릴게요.")
TABS = ["한눈에", "코스", "식당", "병원·약국", "질문지"]
STEP_NAMES = {
    "recommend_places": "갈 만한 장소 찾기", "get_weather": "날씨 확인", "search_food": "식당·카페 찾기",
    "get_place_detail": "코스·시설 살펴보기", "find_nearby_help": "가까운 병원·약국·화장실 찾기",
    "check_nearby_places": "주변 가게 확인", "plan_outing": "반나절 일정 짜기", "ask_user": "필요한 것 여쭤보기",
}
LOADING_STEPS = {
    "food": ["가까운 식당을 찾고 있어요", "식사 조건을 맞춰 보고 있어요", "휠체어로 들어갈 수 있는지 보고 있어요"],
    "place": ["날씨를 확인하고 있어요", "경사와 턱을 살펴보고 있어요", "화장실과 쉴 곳을 찾고 있어요"],
}
NOT_CAUTION = M.NOT_CAUTION


# ---------- 자주 부르는 도구 결과는 저장해 두고 다시 쓴다 ----------
@st.cache_data(show_spinner=False)
def detail_of(place, user_type):
    return T.get_place_detail(place, user_type)


@st.cache_data(show_spinner=False)
def help_of(place, user_type=None):
    return T.find_nearby_help(place, user_type=user_type)


@st.cache_data(show_spinner=False)
def food_of(place, wheel):
    return T.search_food(place=place, prefer_wheelchair=wheel)


@st.cache_data(show_spinner=False)
def nearby_of(place):
    return T.check_nearby_places(place, limit=6)


@st.cache_data(ttl=900, show_spinner=False)
def weather_of(place, when):
    return T.get_weather(place=place, when=when)


# ---------- 동작 ----------
def go(text, user_type=None, open_chat=False):
    """버튼·입력창 콜백. 화면은 그대로 두고, 이번 실행 끝에서 찾는다(대화창에는 '입력 중' 표시)."""
    text = (text or "").strip()
    if not text or S.pending:
        return
    S.msgs.append({"role": "user", "text": text})
    S.pending = (text, user_type)
    if open_chat:
        S.chat_open, S.unread = True, 0


def submit_input():
    go(S.get("chat_text"), open_chat=True)


def toggle_chat():
    S.chat_open = not S.chat_open
    if S.chat_open:
        S.unread = 0


def toggle_panel():
    S.panel_open = not S.panel_open


def set_tab(name):
    S.tab = name


def pick(place):
    S.selected, S.food, S.foods = place, None, []  # 이전 후보의 식당 결과는 버린다


def add_stop(stop):
    """'+ 일정' 버튼: 같은 곳을 두 번 담지 않는다."""
    if stop and all(x["name"] != stop["name"] for x in S.itinerary):
        S.itinerary.append(stop)


def remove_stop(name):
    S.itinerary = [x for x in S.itinerary if x["name"] != name]


def open_plan():
    S.screen, S.panel_open = "plan", True


def result_names():
    return [r["place"] for r in (S.results or {}).get("results") or []]


def show_place(place):
    """대화 속 장소 단추·지도 표식을 누르면 그 장소를 대시보드와 지도에 띄운다."""
    if place in result_names():
        pick(place)
        S.screen, S.tab = "result", "한눈에"
    elif S.detail_only and S.detail_only.get("place") == place:
        S.screen = "answer"
    S.panel_open = True


def to_result():
    S.screen = "result"


def home():
    for k, v in DEFAULTS.items():
        if k not in KEEP:
            S[k] = [] if isinstance(v, list) else v


def first_mentioned(text, names):
    """답변 글에서 가장 먼저 나온 장소 이름."""
    hits = [(text.find(n), -len(n), n) for n in names if n and n in (text or "")]
    return min(hits)[2] if hits else None  # 같은 자리에서 시작하면 긴 이름


def top_place():
    res = (S.results or {}).get("results") or []
    return next((r for r in res if r["place"] == S.selected), res[0] if res else None)


def send(text, user_type=None):
    """사용자 말을 처리하고 대시보드에 보일 내용을 정한다. 버튼으로 이동 유형을 고르면 AI 없이 바로 추천."""
    if user_type:
        S.user_type = user_type
    S.history.append({"role": "user", "content": text})
    S.ask, S.detail_only, S.help_only = None, None, None
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
    names, places, turn_foods = [], [], []
    for name, args, res in out["tool_results"]:
        names.append(name)
        if name == "get_weather" and args.get("when"):
            S.when = args["when"]
        if name == "search_food":  # 한 질문에서 찾은 식당 결과는 모두 보여 준다(예: 횟집과 카페)
            turn_foods.append(res)
            S.diet = args.get("diet_needs") or S.diet
        if name == "plan_outing" and res.get("stops"):  # 반나절 일정 제안
            S.itinerary = res["stops"]
            S.diet = args.get("diet_needs") or S.diet
            places = [x["name"] for x in res["stops"] if x["kind"] == "place"]
        if name == "recommend_places":
            S.results, S.food, S.foods = res, None, []
            S.selected = res["results"][0]["place"] if res["results"] else None
            S.shown = list(dict.fromkeys(S.shown + [r["place"] for r in res["results"]]))
            places = [r["place"] for r in res["results"]]
            if args.get("user_type"):
                S.user_type = args["user_type"]
        if name == "get_place_detail" and "error" not in res:
            if res["place"] in result_names():
                S.selected, S.detail_only = res["place"], None
            else:
                S.detail_only = res
            places = places or [res["place"]]
        if name == "find_nearby_help" and "error" not in res:
            S.help_only = res
    if turn_foods:
        S.foods, S.food = turn_foods, turn_foods[0]
    S.ask = out["ask"]
    said = first_mentioned(out["text"], result_names()) if "recommend_places" in names else None
    if said:  # 하르방이 말로 먼저 꺼낸 장소를 대시보드·지도에도 띄운다(말과 화면이 어긋나지 않게)
        S.selected = said
        places = [said] + [p for p in places if p != said]
    S.msgs.append({"role": "bot", "text": out["text"] or "찾은 내용을 정리했어요.", "places": places,
                   "trace": [STEP_NAMES.get(t["tool"], t["tool"]) for t in out.get("trace", [])]})
    S.typing = len(S.msgs) - 1
    S.history.append({"role": "assistant", "content": out["text"]})

    # 대시보드 내용 고르기(그 밖의 대답이면 대시보드는 그대로 두고 대화창에만 답한다)
    has_results = bool(result_names())
    if S.ask:
        S.chat_open = True
    elif "plan_outing" in names and S.itinerary:
        S.screen = "plan"
    elif "recommend_places" in names:
        S.screen, S.tab = "result", "한눈에"
    elif "search_food" in names:
        if has_results and len(S.foods) == 1 and S.food.get("around") == S.selected:
            S.screen, S.tab = "result", "식당"
        else:
            S.screen = "food"
    elif "find_nearby_help" in names and has_results and S.help_only and S.help_only.get("place") == S.selected:
        S.screen, S.tab, S.help_only = "result", "병원·약국", None
    elif "get_place_detail" in names and has_results and not S.detail_only:
        S.screen, S.tab = "result", "코스"
    elif S.detail_only or S.help_only:
        S.screen = "answer"
    if not S.chat_open:
        S.unread += 1


def process():
    """대기 중인 말을 처리한다. 화면은 그대로 있고, 끝나면 다시 그린다."""
    text, user_type = S.pending
    try:
        send(text, user_type)
    except Exception:  # 무엇이 잘못돼도 대화창에 안내 한 줄
        S.msgs.append({"role": "bot", "text": "찾는 중에 문제가 생겼어요. 한 번 더 말씀해 주세요.", "places": [], "trace": []})
        S.typing = len(S.msgs) - 1
    finally:
        S.pending = None
    st.rerun()


# ---------- 지도 ----------
def map_data():
    top = top_place()
    if S.screen == "result" and top:
        det = detail_of(top["place"], S.user_type)
        food = help_ = None
        if S.tab == "식당":
            food = tab_food(top)
        if S.tab == "병원·약국":
            help_ = help_of(top["place"], S.user_type)
        return M.build(results=S.results["results"], selected=top["place"], detail=det, food=food, help_=help_)
    if S.screen == "plan" and S.itinerary:
        return M.build(stops=S.itinerary)
    if S.screen == "food" and S.foods:
        return M.build(food=S.foods)
    if S.screen == "answer" and (S.detail_only or S.help_only):
        return M.build(detail=S.detail_only, help_=S.help_only)
    return M.build(all_places=T.load()["places"])


def tab_food(top):
    if S.food and S.food.get("around") == top["place"]:
        return S.food
    return food_of(top["place"], "wheelchair" in S.user_type)


def draw_map():
    got = M.render(map_data(), panel=S.panel_open, chat=S.chat_open)
    if got.get("pick"):
        show_place(got["pick"])
        st.rerun()
    if got.get("look"):
        go(f"{got['look']} 코스 자세히 알려줘", open_chat=True)
        st.rerun()


# ---------- 공통 조각 ----------
def condition_texts():
    bits = []
    if S.user_type != "other":
        bits.append(T.USER_TYPES[S.user_type])
    if S.food and S.food.get("diet_labels"):
        bits.append(" · ".join(S.food["diet_labels"]))
    bits.append(S.when)
    where = (S.results or {}).get("area_understood")
    if where:
        bits.append(f"{where} 기준")
    return bits


def state_css():
    """열린 창에 따라 바뀌는 자리(대시보드 위치, 상단 바 폭, 안 읽은 답 표시)."""
    right = 412 if S.chat_open else 16
    used = (right + 420 + 32) if S.panel_open else (412 + 16 if S.chat_open else 32)
    css = [f":root{{--dash-r:{right}px;--top-max:calc(100vw - {used}px)}}"]
    if S.chat_open and S.panel_open:  # 자리가 좁아지면 상단 바는 꼭 필요한 것만
        css.append(".st-key-topbar .chips,.brand small{display:none}"
                   ".st-key-topbar [data-testid=stBaseButton-tertiary] p{display:none}")
    if S.chat_open:  # 가운데 폭 화면에서는 대화창이 열리면 대시보드를 잠시 숨긴다
        css.append("@media (min-width:640px) and (max-width:1180px){.st-key-dash{display:none!important}"
                   ":root{--top-max:calc(100vw - 428px)}}")
    if not S.panel_open:
        css.append("@media (max-width:639.98px){.st-key-chatfab{bottom:20px}.fab-hint{bottom:32px}}")
    if S.unread and not S.chat_open:
        css.append(".st-key-chatfab button::after{content:'" + str(min(S.unread, 9)) + "';position:absolute;top:-2px;right:-2px;"
                   "min-width:24px;height:24px;border-radius:12px;background:#B83227;color:#fff;font-weight:800;font-size:13px;"
                   "display:flex;align-items:center;justify-content:center;border:2px solid #fff}")
    st.html("<style>" + "".join(css) + "</style>")


def topbar():
    with st.container(key="topbar", horizontal=True, vertical_alignment="center", gap="small", wrap=False):
        st.html(U.brand(), width="content")
        if S.screen != "home":
            st.html(U.chips(condition_texts(), gyul_first=S.user_type != "other"), width="content")
        if S.get("big_w") != S.big:
            S.big_w = S.big
        st.toggle("큰 글씨", key="big_w", on_change=lambda: S.__setitem__("big", S.big_w))
        st.button("패널 숨기기" if S.panel_open else "패널 보기", type="tertiary", key="panel_btn", on_click=toggle_panel,
                  icon=":material/right_panel_close:" if S.panel_open else ":material/right_panel_open:")
        if S.screen != "home" or S.msgs:
            st.button("처음으로", icon=":material/home:", type="tertiary", on_click=home, key="to_home")


def shop_card(i, it, prefix):
    with st.container(key=f"card_{prefix}_{i}"):
        tags = [("휠체어 진입 확인", "wc")] if it.get("wheelchair_entry") else []
        fn = it.get("floor_note", "")
        if fn:
            tags.append((fn, "wc" if fn == "1층" else ("gray" if fn == "층 정보 없음" else "")))
        if it.get("baby_chair"):
            tags.append(("아기 의자 있음", "wc"))
        tags += [(w.split(":")[0] + " (추정)", "") for w in it.get("why", [])]
        meta = " · ".join(x for x in (it["food_type"], f"{it['km']}km" if it.get("km") is not None else "",
                                       it.get("address", "")) if x)
        st.html(U.shop(it["name"], meta, tags))
        with st.container(horizontal=True, gap="small"):
            st.link_button("길안내", T.kakao_route_link(it["name"], it["lat"], it["lon"]),
                           icon=":material/directions:", type="primary", key=f"nav_{prefix}_{i}")
            if it.get("phone"):
                st.link_button(f"전화 {it['phone']}", f"tel:{it['phone']}", icon=":material/call:", key=f"tel_{prefix}_{i}")
            if it.get("place_url"):
                st.link_button("카카오맵 정보", it["place_url"], icon=":material/info:", key=f"info_{prefix}_{i}")
            st.button("+ 일정", type="tertiary", key=f"add_{prefix}_{i}", on_click=add_stop, args=(T.food_stop(it),),
                      help="하루 일정에 담기")


def food_list(f, prefix):
    if f.get("anchor_not_found"):
        st.info(f["note"], icon=":material/info:")
        return
    if not f["items"]:
        st.info("조건에 맞는 식당을 찾지 못했어요. 조건을 줄이거나 동네를 바꿔 말해 보세요.", icon=":material/info:")
    for i, it in enumerate(f["items"]):
        shop_card(i, it, prefix)
    st.html(U.src(f["note"]))


def questions(diet_needs=None, prefix="q", place=""):
    st.caption("가기 전에 전화로 이것만 물어보세요. 물어본 것은 눌러서 표시해 두세요.")
    for i, q in enumerate(T.call_questions(S.user_type, diet_needs)):
        st.checkbox(q, key=f"{prefix}_{place}_{i}")


def help_list(h, prefix="h"):
    if "error" in h:
        st.caption(h["error"])
        return
    for kind, items in h.get("help", {}).items():
        for i, it in enumerate(items):
            with st.container(key=f"card_{prefix}_{i}_{kind}"):
                extra = [it.get("status", ""), "기저귀 교환대" if it.get("diaper") else "", it.get("open", "")]
                meta = " · ".join(x for x in [kind, f"{it['km']}km", it.get("address", "")] + extra if x)
                st.html(U.shop(it["name"], meta, []))
                with st.container(horizontal=True, gap="small"):
                    if it.get("lat") is not None:
                        st.link_button("길안내", T.kakao_route_link(it["name"], it["lat"], it["lon"]),
                                       icon=":material/directions:", key=f"nav_{prefix}_{i}_{kind}")
                    if it.get("phone"):
                        st.link_button(f"전화 {it['phone']}", f"tel:{it['phone']}", icon=":material/call:",
                                       key=f"tel_{prefix}_{i}_{kind}")
    st.html(U.src(h.get("note", "")))


def place_overview(top, det):
    where = " · ".join(x for x in (top["where"], f"{top['distance_km']}km 거리" if top.get("distance_km") is not None else "") if x)
    st.html(U.verdict(top["verdict_color"], top["verdict"], top["verdict_reason"]) + U.place_head(top["place"], where))
    if top.get("image"):
        st.image(top["image"], width="stretch", caption="사진: 한국관광공사")
    course = f"약 {top['minutes']}분 · {top['course_m']:,}m" if top.get("minutes") else "시설 방문"
    st.html(U.tiles([
        ("경사", top["slope_level"], "yes" if top["slope_level"] == "완만한 편" else ""),
        ("코스", course, ""),
        ("장애인 화장실", "있어요" if top["accessible_toilet"] else "확인 안 됨", "yes" if top["accessible_toilet"] else "no"),
        ("장애인 주차", "있어요" if top["accessible_parking"] == "yes" else "확인 안 됨",
         "yes" if top["accessible_parking"] == "yes" else "no"),
    ]))
    warn = list(top["watch_out"])
    if top["companion_advised"]:
        warn.insert(0, "동행인과 함께 가는 것을 권해요")
    try:
        wx = weather_of(top["place"], S.when)
    except Exception:  # 예보 값이 비어 있으면 날씨 줄만 빼고 보여 준다
        wx = {}
    weather_html = ""
    if wx.get("available"):
        rain = "확인 안 됨" if wx.get("rain_chance") is None else f"{wx['rain_chance']}%"
        wind = "확인 안 됨" if wx.get("wind_ms") is None else f"{wx['wind_ms']:.0f}m/s"
        line = f"{wx['date']} 비 올 확률 {rain} · 바람 {wind} · {wx['temp']} (Open-Meteo 예보)"
        weather_html = U.weather(line, wx["tips"])
    alt = top.get("rain_alt")
    alt_html = U.weather(f"{alt['name']} ({alt['km']}km · {alt['verdict']})", ["비 오면 대신 갈 곳"]) if alt else ""
    st.html(f"<p style='margin:12px 0 0;font-weight:700'>{U.escape(top['slope_say'])}</p>"
            + U.notes(top["good_points"], warn) + weather_html + alt_html)
    if top.get("overview"):
        with st.expander("장소 소개", icon=":material/info:"):
            st.write(top["overview"])
    st.link_button("카카오맵 길안내", T.kakao_route_link(top["place"], top["lat"], top["lon"]),
                   icon=":material/directions:", type="primary", width="stretch")
    with st.container(horizontal=True, gap="small"):
        if top.get("parking"):
            st.link_button("장애인 주차구역 길안내", top["parking"]["link"], icon=":material/local_parking:",
                           help=f"조사 지점: {top['parking']['label']}")
        if top.get("phone"):
            st.link_button(f"전화 {top['phone']}", f"tel:{top['phone']}", icon=":material/call:")
        if top.get("homepage"):
            st.link_button("홈페이지", top["homepage"], icon=":material/language:")
        st.button("+ 일정", type="tertiary", key="place_add", on_click=add_stop,
                  args=(T.place_stop(top["place"], S.user_type),), help="하루 일정에 담기")
    with st.container(horizontal=True, gap="small"):
        st.button("코스 따라가기", icon=":material/route:", on_click=set_tab, args=("코스",), key="go_course", width="stretch")
        st.button("전화 질문지", icon=":material/call:", on_click=set_tab, args=("질문지",), key="go_ask", width="stretch")
    st.html(U.sect("확인한 것") + U.checks(det["checks"]))
    if len(S.results["results"]) > 1:
        st.html(U.sect("다른 후보"))
        for i, r in enumerate(S.results["results"], 1):
            if r["place"] != top["place"]:
                st.button(f"{i}번 · {r['place']} · {r['verdict']}", key=f"pick_{r['place']}", width="stretch",
                          on_click=pick, args=(r["place"],))
    st.button("본 곳 빼고 새로 찾기", icon=":material/autorenew:", type="tertiary", key="find_new",
              on_click=go, args=("다른 곳 추천해 줘",))
    st.html(U.src(f"자료: {det.get('source') or '제주데이터허브 무장애여행 정보'} · 기준 {det['base_date']}. 현장과 다를 수 있어요."))


# ---------- 대시보드 ----------
def panel_home():
    st.html(U.hero_scene())
    st.html(U.hello())
    for label, icon, ut, text, desc, bg in TYPES:
        with st.container(key=f"choice_{ut}", horizontal=True, vertical_alignment="center", wrap=False):
            st.html(U.choice(icon, label, desc, bg), width="stretch")
            st.button("찾기", icon=":material/arrow_forward:", type="primary", key=f"type_{ut}",
                      on_click=go, args=(text, ut))
    st.html(U.tip_line("지도의 초록 점을 누르면 그 장소를 바로 살펴볼 수 있어요. "
                       "더 자세한 건 오른쪽 아래 하르방에게 물어보세요."))


def panel_result():
    top = top_place()
    if not top:
        st.info("조건에 맞는 곳을 더 찾지 못했어요. 동네나 분위기를 바꿔서 말해 보세요.", icon=":material/info:")
        return
    n = len(S.results["results"])
    idx = result_names().index(top["place"]) + 1
    st.html(U.dash_head("추천 결과", f"{n}곳 중 {idx}번"))
    if S.get("tab_w") != S.tab:
        S.tab_w = S.tab
    st.segmented_control("화면", TABS, key="tab_w", label_visibility="collapsed", width="stretch",
                         on_change=lambda: S.__setitem__("tab", S.tab_w or S.tab))
    det = detail_of(top["place"], S.user_type)
    if S.tab == "한눈에":
        place_overview(top, det)
    elif S.tab == "코스":
        facility = det.get("data_kind") == "시설(관광공사)"
        st.html(U.place_head(top["place"], "시설 방문" if facility else
                             f"약 {det['minutes']}분 · {det['course_m']:,}m · 경사 {det['slope_level']}"))
        if det["key_points"]:
            st.caption("지도의 빨간 ! 표시가 아래 빨간 점 지점이에요.")
            st.html(U.timeline(det["key_points"], NOT_CAUTION))
        elif facility:
            entry = (det.get("all_points") or [{}])[0].get("text", "")
            st.caption("시설 입구 기준 정보예요. 코스를 따라 경사를 잰 자료는 아니에요.")
            if entry:
                st.html(U.notes([entry], []))
        else:
            st.caption("특별히 확인할 지점 기록이 없어요.")
        if det.get("toilets_near"):
            st.html(U.sect("가까운 장애인 화장실") + U.notes(
                [f"{t['name']} ({int(t['km'] * 1000)}m){' · 기저귀 교환대' if t.get('diaper') else ''}"
                 + (f" · {t['open']}" if t.get("open") else "") for t in det["toilets_near"]], []))
        if det.get("bus_stops"):
            st.html(U.sect("가까운 버스 정류소") + U.notes(
                [f"{b['name']} · 걸어서 약 {b['walk_min']}분({b['m']}m)" for b in det["bus_stops"]],
                ["저상버스·노선은 확인이 안 됐어요"]))
        if det.get("source"):
            st.html(U.src(det["source"]))
    elif S.tab == "식당":
        f = tab_food(top)
        cond = " · ".join(f.get("diet_labels") or [])
        st.html(U.sect(f"{top['place']} 근처 {cond or '식당'}"))
        food_list(f, "tf")
        near = nearby_of(top["place"])
        if near["items"]:
            with st.expander("2021년 조사 때 있던 가게 (2025 영업 확인)", icon=":material/storefront:"):
                status = {"영업 확인": ("2025 영업 확인", "wc"), "확인 안 됨": ("영업 확인 안 됨", "gray"),
                          "폐업 기록": ("폐업 기록", "red")}
                for i, it in enumerate(near["items"]):
                    tags = [status.get(it["open_status"], (it["open_status"], "gray"))]
                    if it["wheelchair_entry"]:
                        tags.append(("휠체어 진입", "wc"))
                    with st.container(key=f"card_near_{i}"):
                        st.html(U.shop(it["name"], f"{it['category']} · {it['km']}km", tags))
                st.html(U.src(near["note"]))
    elif S.tab == "병원·약국":
        st.html(U.sect(f"{top['place']}에서 가까운 곳"))
        help_list(help_of(top["place"], S.user_type))
    elif S.tab == "질문지":
        st.html(U.sect("전화로 물어볼 것"))
        questions(S.diet or (S.food or {}).get("diet_needs"), prefix="qr", place=top["place"])


def back_button(key):
    if top_place():
        st.button(f"{S.selected} 결과로 돌아가기", icon=":material/arrow_back:", type="tertiary",
                  key=key, on_click=to_result)


def panel_food():
    total = sum(len(f.get("items", [])) for f in S.foods)
    st.html(U.dash_head("식당·카페", f"{total}곳"))
    back_button("back_result")
    for fi, f in enumerate(S.foods):
        cond = " · ".join(f.get("diet_labels") or [])
        kind = f.get("food_kind") or "식당"
        st.html(U.sect(f"{f['around']} 근처 {kind}" + (f" · {cond}" if cond else "")))
        food_list(f, f"sf{fi}")
    with st.expander("전화로 물어볼 것", icon=":material/call:", expanded=bool(S.diet)):
        questions(S.diet, prefix="qf", place=S.food.get("around") or "")


def panel_plan():
    st.html(U.dash_head("오늘 일정", f"{len(S.itinerary)}곳"))
    back_button("back_result3")
    legs = T.itinerary_legs(S.itinerary)
    for i, stop in enumerate(S.itinerary):
        if i:
            st.caption(f"↓ 약 {legs[i - 1]['km']}km (직선)")
        with st.container(key=f"card_plan_{i}"):
            label = stop["verdict"] if stop["kind"] == "place" else stop.get("food_type", "")
            tags = [(f"비 오면: {stop['rain_alt']['name']}", "")] if stop.get("rain_alt") else []
            st.html(U.shop(f"{i + 1}. {stop['name']}", label, tags))
            with st.container(horizontal=True, gap="small"):
                st.link_button("길안내", T.kakao_route_link(stop["name"], stop["lat"], stop["lon"]),
                               icon=":material/directions:", key=f"it_nav_{i}")
                st.button("빼기", type="tertiary", key=f"it_del_{i}", on_click=remove_stop, args=(stop["name"],))
    if S.itinerary:
        sheet = T.itinerary_html(S.itinerary, S.user_type, S.diet, S.when)
        st.download_button("일정표 내려받기", data=sheet.encode("utf-8"), file_name="같이나들이_일정표.html",
                           mime="text/html", icon=":material/print:", type="primary", width="stretch",
                           help="내려받은 파일을 열어 인쇄하거나 PDF로 저장하세요")
        st.html(U.src("일정표: 들르는 순서·거리, 장소별 확인표, 가까운 장애인 화장실, 급할 때 연락처, 전화로 확인할 것"))
    else:
        st.caption("담은 곳이 없어요. 장소나 식당 카드의 '+ 일정'을 눌러 담아 보세요.")


def panel_answer():
    st.html(U.dash_head("장소 정보"))
    back_button("back_result2")
    d = S.detail_only if S.detail_only and "verdict" in S.detail_only else None
    if d:
        st.html(U.verdict(d["verdict_color"], d["verdict"], d["verdict_reason"]) + U.place_head(d["place"], d["where"]))
        st.html(U.sect("확인한 것") + U.checks(d["checks"]))
        if d["key_points"]:
            st.html(U.sect("코스 따라가기") + U.timeline(d["key_points"], NOT_CAUTION))
    if S.help_only:
        st.html(U.sect(f"{S.help_only['place']}에서 가까운 곳"))
        help_list(S.help_only, prefix="ha")


def dashboard():
    if not S.panel_open:
        return
    with st.container(key="dash", gap="small"):
        if S.itinerary and S.screen != "plan":
            st.button(f"오늘 일정 {len(S.itinerary)}곳 보기", icon=":material/route:", type="secondary",
                      key="open_plan", on_click=open_plan, width="stretch")
        if S.screen == "plan":
            panel_plan()
        elif S.screen == "result" and S.results:
            panel_result()
        elif S.screen == "food" and S.foods:
            panel_food()
        elif S.screen == "answer" and (S.detail_only or S.help_only):
            panel_answer()
        else:
            S.screen = "home"
            panel_home()


# ---------- 하르방 버튼과 대화창 ----------
def chat_fab():
    label = "하르방 도우미 닫기" if S.chat_open else "하르방 도우미에게 물어보기"
    st.button(label, key="chatfab", on_click=toggle_chat)
    if not S.chat_open and not S.msgs:
        st.html(U.fab_hint())


def bot_msg(i, m, animate=False):
    with st.container(key=f"bot_{i}", horizontal=True, gap="small", vertical_alignment="top", wrap=False):
        st.html(U.avatar(), width="content")
        with st.container(key=f"botb_{i}", gap="small"):
            text = m["text"]
            if animate:  # 한 글자씩 써 내려가듯이(전체 1.5초 안쪽)
                ph = st.empty()
                step = max(2, len(text) // 50)
                for k in range(step, len(text), step):
                    ph.markdown(text[:k] + " ▍")
                    time.sleep(0.03)
                ph.markdown(text)
            else:
                st.markdown(text)
            if m.get("trace"):
                st.html(U.trace(m["trace"]))
            shown = result_names() + ([S.detail_only["place"]] if S.detail_only else [])
            places = [p for p in m.get("places", []) if p in shown]
            if places:
                with st.container(key=f"mplaces_{i}", horizontal=True, gap="small"):
                    for j, p in enumerate(places):
                        st.button(p, key=f"mp_{i}_{j}", icon=":material/location_on:", type="secondary",
                                  on_click=show_place, args=(p,))


def chat_window():
    if not S.chat_open:
        S.typing = None
        return
    animate = S.typing
    S.typing = None  # 한 번만 움직인다(중간에 다시 그려져도 다시 안 움직임)
    with st.container(key="chatwin"):
        with st.container(key="chathead", horizontal=True, vertical_alignment="center", wrap=False):
            st.html(U.chat_head(), width="stretch")
            st.button("닫기", icon=":material/close:", type="tertiary", key="chat_close", on_click=toggle_chat)
        with st.container(key="chatlog"):
            with st.container(key="chatlist", gap="small"):
                bot_msg("hi", {"text": GREETING})
                if not S.msgs:
                    st.caption("이렇게 말해도 돼요")
                    with st.container(key="examples", horizontal=True, gap="small"):
                        for ex in EXAMPLES:
                            st.button(ex, key=f"ex_{ex}", on_click=go, args=(ex, None, True))
                for i, m in enumerate(S.msgs):
                    if m["role"] == "user":
                        st.html(U.msg_user(m["text"]))
                    else:
                        bot_msg(i, m, animate=(i == animate and not S.pending))
                if S.ask and not S.pending:
                    with st.container(key="askopts", horizontal=True, gap="small"):
                        for opt in dict.fromkeys(str(o) for o in (S.ask.get("options") or [])):
                            st.button(opt, type="primary", key=f"opt_{opt}", on_click=go, args=(opt, None, True))
                if S.pending:
                    text = S.pending[0]
                    food_q = any(w in text for w in ("식당", "밥", "카페", "먹", "음식", "맛집"))
                    st.html(U.typing(LOADING_STEPS["food" if food_q else "place"]))
        placeholder = "예: 아빠가 휠체어 타요. 바다 보고 싶어요" if not S.msgs else "더 물어보세요 (예: 근처 씹기 편한 음식점)"
        st.chat_input(placeholder, key="chat_text", on_submit=submit_input)


# ---------- 그리기 ----------
st.html(U.CSS + U.FAB_CSS)
if S.big:
    st.html(U.BIG_CSS)
state_css()
draw_map()
topbar()
dashboard()
chat_fab()
if S.pending:
    st.html(U.searching())
chat_window()
if S.pending:
    process()
