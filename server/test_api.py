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

from server.api import app, T

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
