"""FastAPI 서버 - 제주 같이나들이 백엔드.

실행: .venv/Scripts/python -m uvicorn server.api:app --reload --port 8000
"""
import csv
import math
import os
import sys
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# app/ 폴더를 경로에 추가해 agent, tools를 import한다
_APP_DIR = str(Path(__file__).resolve().parents[1] / "app")
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

import agent as A  # noqa: E402
import tools as T  # noqa: E402

# ---------- 앱 초기화 ----------
app = FastAPI(title="제주 같이나들이 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- JSON 안전 변환 ----------
def clean(obj: Any) -> Any:
    """pandas/numpy 값, NaN/inf, tuple, DataFrame을 기본 파이썬 값으로 바꾼다."""
    # pandas DataFrame
    try:
        import pandas as pd
        if isinstance(obj, pd.DataFrame):
            return clean(obj.to_dict(orient="records"))
        if isinstance(obj, pd.Series):
            return clean(obj.to_dict())
    except ImportError:
        pass

    # numpy 스칼라
    try:
        import numpy as np
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            v = float(obj)
            if math.isnan(v) or math.isinf(v):
                return None
            return v
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return clean(obj.tolist())
    except ImportError:
        pass

    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    return obj


# ---------- 장소 추가 정보 (사진·주소) ----------
def _load_place_info() -> dict:
    """data/processed/place_info.csv를 로드해 {place: {address, photos}} 반환.

    파일이 없으면 빈 사전을 반환한다.
    """
    csv_path = Path(__file__).resolve().parents[1] / "data" / "processed" / "place_info.csv"
    if not csv_path.exists():
        return {}
    result: dict = {}
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            photos_raw = row.get("photos", "").strip()
            photos = [p for p in photos_raw.split("|") if p] if photos_raw else []
            result[row["place"]] = {
                "address": row.get("address", "") or None,
                "photos": photos,
            }
    return result


_PLACE_INFO: dict = _load_place_info()


# ---------- 캐시 ----------
_weather_cache: dict = {}  # key -> (timestamp, result)
_WEATHER_TTL = 15 * 60  # 15분


def _cached_weather(place: str, when: str) -> dict:
    key = (place, when)
    hit = _weather_cache.get(key)
    if hit and time.time() - hit[0] < _WEATHER_TTL:
        return hit[1]
    try:
        result = T.get_weather(place=place, when=when)
    except Exception:
        result = {}
    _weather_cache[key] = (time.time(), result)
    return result


@lru_cache(maxsize=256)
def _cached_detail(place: str, user_type: str) -> dict:
    return T.get_place_detail(place, user_type)


@lru_cache(maxsize=256)
def _cached_help(place: str) -> dict:
    return T.find_nearby_help(place)


@lru_cache(maxsize=256)
def _cached_food(place: str, wheel: bool) -> dict:
    return T.search_food(place=place, prefer_wheelchair=wheel)


@lru_cache(maxsize=256)
def _cached_nearby(place: str) -> dict:
    return T.check_nearby_places(place, limit=6)


# ---------- 엔드포인트 ----------

@app.get("/api/config")
def config():
    return clean({
        "kakao_js_key": os.getenv("KAKAO_JS_KEY", ""),
        "ai": A.available(),
        "user_types": T.USER_TYPES,
        "food_kinds": list(T.FOOD_KINDS.keys()),
        "diet_needs": {k: v["label"] for k, v in T.DIET_NEEDS.items()},
    })


@app.get("/api/places")
def places():
    df = T.load()["places"]
    result = []
    for _, r in df.iterrows():
        name = r["place"]
        info = _PLACE_INFO.get(name, {})
        result.append({
            "place": name,
            "lat": float(r["start_lat"]),
            "lon": float(r["start_lon"]),
            "sigungu": r["sigungu"],
            "dong": r["dong"],
            "address": info.get("address") or None,
            "photos": info.get("photos") or [],
        })
    return clean(result)


# ---------- /api/chat ----------
class ChatRequest(BaseModel):
    text: str
    user_type: Optional[str] = None
    history: list = []
    known_user_type: Optional[str] = None
    last_place: Optional[str] = None
    location: Optional[list] = None
    shown_places: Optional[list] = None


@app.post("/api/chat")
def chat(req: ChatRequest):
    fallback = False
    if req.user_type:
        out = A.rule_mode(req.text, req.user_type)
    else:
        known = req.known_user_type
        location = tuple(req.location) if req.location else None
        shown = list(req.shown_places) if req.shown_places else None
        try:
            if A.available():
                out = A.run(req.history, known, req.last_place, location, shown)
            else:
                out = A.rule_mode(req.text, known)
        except Exception:
            out = A.rule_mode(req.text, known)
            out["text"] = "(AI 연결이 안 돼서 기본 모드로 찾았어요) " + out["text"]
            fallback = True

    # tool_results: (name, args, result) 튜플 -> dict
    tool_results = [
        {"name": name, "args": clean(args), "result": clean(result)}
        for name, args, result in out.get("tool_results", [])
    ]

    return clean({
        "text": out.get("text", ""),
        "ask": out.get("ask"),
        "tool_results": tool_results,
        "trace": out.get("trace", []),
        "fallback": fallback,
    })


@app.get("/api/detail")
def detail(place: str = Query(...), user_type: str = Query("other")):
    return clean(_cached_detail(place, user_type))


@app.get("/api/help")
def help_(place: str = Query(...)):
    return clean(_cached_help(place))


@app.get("/api/food")
def food(place: str = Query(...), wheel: bool = Query(False)):
    return clean(_cached_food(place, wheel))


@app.get("/api/nearby")
def nearby(place: str = Query(...)):
    return clean(_cached_nearby(place))


@app.get("/api/weather")
def weather(place: str = Query(...), when: str = Query("오늘")):
    return clean(_cached_weather(place, when))


@app.get("/api/questions")
def questions(
    user_type: str = Query("other"),
    diet_needs: Optional[str] = Query(None),
):
    needs = [d.strip() for d in diet_needs.split(",") if d.strip()] if diet_needs else []
    return clean(T.call_questions(user_type, needs))


@app.get("/api/route-link")
def route_link(name: str = Query(...), lat: float = Query(...), lon: float = Query(...)):
    return {"url": T.kakao_route_link(name, lat, lon)}

