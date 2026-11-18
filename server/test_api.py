"""FastAPI TestClient 연기 테스트 - 모든 GET 엔드포인트와 /api/chat(rule_mode 경로).

실행: .venv/Scripts/python -m pytest server/test_api.py -q
"""
import sys
from pathlib import Path

# 저장소 루트를 sys.path에 추가(import server.api 가능하게)
_ROOT = str(Path(__file__).resolve().parents[1])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from fastapi.testclient import TestClient

from server.api import app, A, T

client = TestClient(app)

# 테스트용 첫 번째 장소
_FIRST_PLACE = T.load()["places"].iloc[0]["place"]


# ---------- GET 엔드포인트 ----------

def test_config():
    r = client.get("/api/config")
    assert r.status_code == 200
    data = r.json()
    assert "kakao_js_key" in data
    assert "ai" in data
    assert "user_types" in data
    assert "food_kinds" in data
    assert "diet_needs" in data


def test_places():
    r = client.get("/api/places")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0
    item = data[0]
    assert "place" in item
    assert "lat" in item
    assert "lon" in item
    assert "sigungu" in item
    assert "dong" in item
    # 추가 필드: address (str | None), photos (list[str])
    assert "address" in item
    assert "photos" in item
    assert isinstance(item["photos"], list)
    assert item["address"] is None or isinstance(item["address"], str)
    # 최소 한 장소는 사진이 있어야 한다
    places_with_photos = [p for p in data if p["photos"]]
    assert len(places_with_photos) > 0, "사진이 있는 장소가 하나도 없음"
    # 최소 한 장소는 주소가 있어야 한다
    places_with_addr = [p for p in data if p["address"]]
    assert len(places_with_addr) > 0, "주소가 있는 장소가 하나도 없음"


def test_detail():
    r = client.get("/api/detail", params={"place": _FIRST_PLACE, "user_type": "manual_wheelchair"})
    assert r.status_code == 200
    data = r.json()
    # 장소 이름 또는 에러 키
    assert "place" in data or "error" in data
    if "place" in data:
        assert "all_points" in data  # 계약: all_points 포함


def test_help():
    r = client.get("/api/help", params={"place": _FIRST_PLACE})
    assert r.status_code == 200
    data = r.json()
    assert "place" in data or "error" in data


# ---------- 제주데이터허브 OpenAPI 자료(07_hub_api.py) ----------

def test_bus_stops_in_detail_and_help():
    """가문동해안길 출발점 150m 거리에 '가문동포구 입구' 정류소가 있다."""
    d = client.get("/api/detail", params={"place": "가문동해안길"}).json()
    assert d["bus_stops"] and d["bus_stops"][0]["name"] == "가문동포구 입구"
    assert d["bus_stops"][0]["m"] <= 300
    h = client.get("/api/help", params={"place": "가문동해안길"}).json()
    assert h["bus"][0]["name"] == "가문동포구 입구"


def test_closed_pharmacy_excluded():
    """약국 정보 API에 폐업으로만 남은 약국은 가까운 약국 목록에서 빠진다."""
    med = T.load()["medical"]
    closed = [(n, a) for n, a in zip(med["name"], med["address"]) if T.pharmacy_status(n, a) == "폐업"]
    assert closed, "폐업으로 판정된 약국이 하나는 있어야 한다"
    shown = set()
    for p in T.load()["places"]["place"]:
        shown |= {x["name"] for x in T.find_nearby_help(p)["help"]["약국"]}
    assert not shown & {n for n, _ in closed}


def test_food():
    r = client.get("/api/food", params={"place": _FIRST_PLACE, "wheel": "false"})
    assert r.status_code == 200
    data = r.json()
    assert "items" in data


def test_nearby():
    r = client.get("/api/nearby", params={"place": _FIRST_PLACE})
    assert r.status_code == 200
    data = r.json()
    assert "items" in data


def test_weather():
    r = client.get("/api/weather", params={"place": _FIRST_PLACE, "when": "오늘"})
    assert r.status_code == 200
    data = r.json()
    # 예외 시 {} 반환, 아니면 available 키 존재
    assert isinstance(data, dict)


def test_questions():
    r = client.get("/api/questions", params={"user_type": "manual_wheelchair"})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_questions_with_diet():
    r = client.get("/api/questions", params={"user_type": "senior", "diet_needs": "soft,mild"})
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


def test_route_link():
    r = client.get("/api/route-link", params={"name": _FIRST_PLACE, "lat": 33.5, "lon": 126.5})
    assert r.status_code == 200
    data = r.json()
    assert "url" in data
    assert "kakao" in data["url"]


# ---------- POST /api/chat (rule_mode 경로: user_type 있음) ----------

def test_chat_rule_mode():
    payload = {
        "text": "휠체어 타는 가족과 나들이 갈 곳 추천해 줘",
        "user_type": "manual_wheelchair",
        "history": [],
    }
    r = client.post("/api/chat", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "text" in data
    assert "ask" in data
    assert "tool_results" in data
    assert "trace" in data
    assert "fallback" in data
    # tool_results 각 항목 모양 확인
    for tr in data["tool_results"]:
        assert "name" in tr
        assert "args" in tr
        assert "result" in tr


def test_chat_no_user_type_no_ai():
    """AI 없이 규칙 모드로 fallback되는 경로 (OPENAI_API_KEY 없는 환경)."""
    payload = {
        "text": "휠체어 타는 가족과 나들이 갈 곳 추천해 줘",
        "user_type": None,
        "history": [{"role": "user", "content": "휠체어 타는 가족과 나들이 갈 곳 추천해 줘"}],
        "known_user_type": "manual_wheelchair",
        "last_place": None,
        "location": None,
        "shown_places": [],
    }
    r = client.post("/api/chat", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "text" in data
    assert isinstance(data["tool_results"], list)


# ---------- 성인 전용 장소·조사(josa)·출입 문구 (tools.py 회귀) ----------

def _exhaust(user_type, lat, lon, rounds=8, limit=5):
    """'다른 곳'을 여러 번 누른 것처럼 exclude를 늘려 가며 추천을 받는다."""
    shown, seen = [], []
    for _ in range(rounds):
        res = T.recommend_places(user_type=user_type, limit=limit, origin_lat=lat, origin_lon=lon, exclude=shown)["results"]
        new = [x for x in res if x["place"] not in shown]
        if not new:
            break
        shown += [x["place"] for x in new]
        seen += new
    return seen


def _adult_rows():
    pl = T.load()["places"]
    return [r for _, r in pl.iterrows() if T.is_adult_only(r)]


def test_adult_only_places_exist():
    assert _adult_rows(), "데이터에 성인 전용 장소가 있어야 아래 테스트가 의미가 있다"


def test_stroller_never_gets_adult_only():
    """유모차 가족: 성인 전용 장소 바로 옆에서 '다른 곳'을 여러 번 눌러도 성인 전용 장소가 안 나온다."""
    adult = {r["place"] for r in _adult_rows()}
    for r in _adult_rows():
        seen = _exhaust("stroller", float(r["start_lat"]), float(r["start_lon"]))
        assert len(seen) >= 20
        names = {x["place"] for x in seen} | {x["rain_alt"]["name"] for x in seen if x.get("rain_alt")}
        assert not names & adult, names & adult
        assert not [x["place"] for x in seen if any("성인만 입장" in w for w in x["watch_out"])]
    for theme in ("실내", "역사·문화", None):
        res = T.recommend_places(user_type="stroller", area="안덕", theme=theme, limit=5)["results"]
        assert not {x["place"] for x in res} & adult


def test_senior_gets_adult_only_warning():
    """어르신 가족에게는 빼지 않고 '성인만 입장' 주의를 붙인다(위 유모차 테스트의 대조군)."""
    adult = {r["place"] for r in _adult_rows()}
    for r in _adult_rows():
        seen = _exhaust("senior", float(r["start_lat"]), float(r["start_lon"]))
        hit = [x for x in seen if x["place"] == r["place"]]
        assert hit, f"{r['place']} 이 근처 추천에 한 번은 나와야 한다"
        assert any("성인만 입장" in w for w in hit[0]["watch_out"])
        warned = {x["place"] for x in seen if any("성인만 입장" in w for w in x["watch_out"])}
        assert warned <= adult  # 경고는 성인 전용 장소에만 붙는다


def test_josa():
    cases = [("곽지해수욕장", "을를", "을"), ("제주러브랜드", "을를", "를"), ("감귤박물관", "을를", "을"),
             ("건강과 성 박물관(제주)", "을를", "을"),  # 괄호 꼬리 '(제주)'는 건너뜀: '관'의 받침
             ("가파도 소망전망대", "이가", "가"), ("서귀포", "은는", "는"), ("턱 11.5cm", "이가", "가"),
             ("계단 2곳", "이가", "이"), ("올레 7", "을를", "을"), ("올레 2", "을를", "를"),
             ("경사", "이가", "가"), ("턱", "은는", "은"),
             ("서귀포", "으로", "로"), ("제주시청", "으로", "으로"), ("애월", "으로", "로"), ("올레 7", "으로", "로")]
    for word, pair, want in cases:
        assert T.josa(word, pair) == word + want, (word, pair, T.josa(word, pair))
    assert T.join_and(["경사", "턱", "계단"]) == "경사, 턱과 계단"


def test_entry_say_stroller_wording():
    """관광공사 '휠체어 접근 가능함'은 휠체어가 아닌 가족에게 '휠체어·유모차도 들어갈 수 있음'으로 보인다."""
    pl = T.load()["places"]
    tour = pl[pl["survey"] == T.TOUR_SURVEY]
    raw_hits = tour[tour["entry_access"].fillna("").str.contains("휠체어 접근 가능함")]
    assert len(raw_hits) > 0
    for _, r in raw_hits.iterrows():
        for ut in ("stroller", "senior", "pregnant", "other"):
            s = T.access_summary(r, ut)
            assert "휠체어 접근 가능" not in s["verdict_reason"], (r["place"], ut)
            assert "휠체어 접근 가능" not in s["checks"][0]["status"]
            assert "있음해요" not in s["verdict_reason"] and "수 있음." not in s["verdict_reason"][-6:]
        assert "휠체어 접근 가능" in T.access_summary(r, "manual_wheelchair")["verdict_reason"]  # 휠체어는 원래 문구
    assert (T.entry_say("출입구까지 턱이 없어 휠체어 접근 가능함", "stroller")
            == "출입구까지 턱이 없어 휠체어·유모차도 들어갈 수 있음")
    for x in T.recommend_places(user_type="stroller", limit=5)["results"]:
        assert "휠체어 접근 가능함" not in x["verdict_reason"] + x["slope_say"]


def test_no_fixed_particles():
    """'을(를)', '이(가)'처럼 조사를 둘 다 적은 문장이 답에 나오지 않는다."""
    texts = ["휠체어 타는 가족과 갈 곳 추천해 줘", "유모차로 애월 바다 가고 싶어", "부모님 모시고 서귀포 숲 산책",
             "임산부랑 화장실 있는 곳", "전동 휠체어로 역사 유적"]
    for t in texts:
        for ut in ("manual_wheelchair", "electric_wheelchair", "stroller", "senior", "pregnant"):
            out = A.rule_mode(t, ut)
            assert "(를)" not in out["text"]
            top = out["tool_results"][0][2]["results"][0]["place"]
            assert out["text"].startswith(f"**{top}** 추천해요.")
    pl = T.load()["places"]
    for _, r in pl.iterrows():
        for ut in T.USER_TYPES:
            assert "(가)" not in T.access_summary(r, ut)["verdict_reason"]


def test_weather_place_not_invented(monkeypatch):
    """사용자가 장소를 말하지 않았는데 모델이 get_weather(place='귀덕해안길')처럼 장소를 골라 넣으면 코드가 뺀다."""
    from types import SimpleNamespace as NS
    import json as _json
    import openai

    calls = []
    script = [[("get_weather", {"place": "귀덕해안길", "when": "내일"})],
              [("get_weather", {"place": "가문동해안길", "when": "내일"})], None]

    class FakeClient:
        def __init__(self, *a, **k):
            self.chat = NS(completions=NS(create=self.create))

        def create(self, **kw):
            step = script[len(calls)]
            calls.append(kw)
            tcs = None if step is None else [
                NS(id=f"c{i}", function=NS(name=n, arguments=_json.dumps(a, ensure_ascii=False)),
                   model_dump=lambda n=n, a=a, i=i: {"id": f"c{i}", "type": "function",
                                                     "function": {"name": n, "arguments": _json.dumps(a)}})
                for i, (n, a) in enumerate(step)]
            return NS(choices=[NS(message=NS(content="" if tcs else "바람이 강해요.", tool_calls=tcs))])

    seen = []
    fake_wx = lambda **kw: seen.append(kw) or {"available": True, "where": kw.get("place") or kw.get("area") or "제주시"}
    monkeypatch.setattr(openai, "OpenAI", FakeClient)
    monkeypatch.setattr(T, "get_weather", fake_wx)
    monkeypatch.setitem(A.TOOL_FUNCS, "get_weather", fake_wx)
    q = "내일 바람 많이 불면 휠체어로 해안길 가도 괜찮을까?"
    out = A.run([{"role": "user", "content": q}])
    wx_calls = [a for n, a, _ in out["tool_results"] if n == "get_weather"]
    assert len(wx_calls) >= 2 and all("place" not in a for a in wx_calls), wx_calls
    assert len(calls) == 3  # 모델 호출 3번(도구 두 번 + 답변)
    # 직전 추천 장소라면 그대로 쓴다
    calls.clear()
    out = A.run([{"role": "user", "content": q}], last_place="가문동해안길")
    assert any(a.get("place") == "가문동해안길" for n, a, _ in out["tool_results"] if n == "get_weather")


def test_chat_rule_mode_josa():
    r = client.post("/api/chat", json={"text": "유모차로 바다 보러", "user_type": "stroller", "history": []}).json()
    assert "을(를)" not in r["text"]


# ---------- 판정 근거(evidence) ----------

EVIDENCE_KEYS = {"kind", "summary", "source", "survey", "base_date", "used_count", "items"}
ITEM_KEYS = {"label", "text", "flags", "at_m", "on_route", "used", "lat", "lon"}
VERDICT_FLAG = ("경사 약", "턱 ", "계단", "진입 어려움")


def _check_evidence(ev):
    assert set(ev) == EVIDENCE_KEYS
    assert ev["kind"] in ("course", "facility")
    for it in ev["items"]:
        assert set(it) == ITEM_KEYS
        assert isinstance(it["flags"], list) and isinstance(it["text"], str)
    used = [it["used"] for it in ev["items"]]
    assert used == sorted(used, reverse=True), "판정에 쓴 기록이 먼저 와야 한다"
    assert ev["used_count"] == sum(used)


def test_evidence_course_detail():
    d = T.get_place_detail("가문동해안길", "manual_wheelchair")
    ev = d["evidence"]
    _check_evidence(ev)
    pts = T.load()["points"]
    n = int((pts["place"] == "가문동해안길").sum())
    assert ev["kind"] == "course" and ev["source"] == "제주데이터허브 무장애여행 위치정보"
    assert len(ev["items"]) == n and f"조사 지점 {n}곳" in ev["summary"]
    assert ev["base_date"] == "2021-12-22"
    first = ev["items"][0]
    assert first["used"] and "턱 11.5cm" in first["flags"] and "11.5cm" in first["text"]  # 원문 그대로
    for it in ev["items"]:
        assert it["used"] == (bool(it["on_route"]) and any(f.startswith(VERDICT_FLAG) for f in it["flags"]))
    used = [it for it in ev["items"] if it["used"]]
    assert [it["at_m"] for it in used] == sorted(it["at_m"] for it in used)  # 판정 지점은 코스 순서대로
    assert set(d["all_points"][0]) == {"at_m", "label", "text", "flags", "lat", "lon"}  # 기존 모양 그대로


def test_evidence_all_course_places():
    pl = T.load()["places"]
    for p in pl[pl["survey"] != T.TOUR_SURVEY]["place"]:
        ev = T.place_evidence(p)
        _check_evidence(ev)
        assert ev["kind"] == "course" and ev["items"], p
        r = pl[pl["place"] == p].iloc[0]
        stairs_used = [it for it in ev["items"] if it["used"] and "계단" in it["flags"]]
        assert len(stairs_used) == int(r["route_stairs_points"]), p  # 판정의 계단 수 = 근거 지점 수


def test_evidence_tour_place():
    ev = T.get_place_detail("건강과 성 박물관(제주)", "stroller")["evidence"]
    _check_evidence(ev)
    assert ev["kind"] == "facility" and ev["source"] == "한국관광공사 무장애 여행 정보"
    labels = [it["label"] for it in ev["items"]]
    assert labels[0] == "출입 경로" and ev["items"][0]["used"]
    assert {"장애인 화장실", "엘리베이터", "휠체어 대여", "유모차 대여"} <= set(labels)
    assert ev["items"][0]["text"] == "출입구까지 경사로가 있어 휠체어 접근 가능함"  # 원문(바꿔 쓰지 않음)


def test_evidence_in_recommend_and_hidden_from_llm():
    rec = T.recommend_places(user_type="senior", area="애월", limit=5)
    assert rec["results"]
    for x in rec["results"]:
        _check_evidence(x["evidence"])
    view = A._llm_view("recommend_places", rec)
    assert '"evidence"' not in view and rec["results"][0]["place"] in view
    assert all("evidence" in x for x in rec["results"])  # 원래 결과(화면용)는 그대로
    det = T.get_place_detail("가문동해안길")
    dv = A._llm_view("get_place_detail", det)
    assert '"evidence"' not in dv and '"all_points"' not in dv and "evidence" in det


def test_api_evidence_fields():
    d = client.get("/api/detail", params={"place": "가문동해안길", "user_type": "stroller"}).json()
    _check_evidence(d["evidence"])
    chat = client.post("/api/chat", json={"text": "휠체어로 바다", "user_type": "manual_wheelchair", "history": []}).json()
    for x in chat["tool_results"][0]["result"]["results"]:
        _check_evidence(x["evidence"])
    places = client.get("/api/places").json()
    assert set(places[0]) == {"place", "lat", "lon", "sigungu", "dong", "address", "photos"}  # 기존 모양 유지
