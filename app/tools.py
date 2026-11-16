"""Agent가 호출하는 도구들.

모든 판단(순위, 거리, 난이도 문장)은 코드로 계산한다. 같은 입력이면 같은 결과가 나온다.
AI는 사용자의 말을 이 도구들의 입력으로 바꾸고, 결과를 쉬운 말로 전달하는 역할만 한다.
"""
import math
import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

PROC = Path(__file__).resolve().parents[1] / "data" / "processed"

USER_TYPES = {
    "manual_wheelchair": "수동 휠체어",
    "electric_wheelchair": "전동 휠체어",
    "stroller": "유모차",
    "senior": "어르신(보행)",
    "other": "기타",
}
# companion.csv의 이동유형 이름과 연결
COMPANION_KEY = {
    "manual_wheelchair": "휠체어 이용인(수동)",
    "electric_wheelchair": "휠체어 이용인(전동)",
    "stroller": "영유아",
    "senior": "시니어",
}
# 상대 난이도별 감점. 수동 휠체어·유모차는 경사에 가장 민감하다고 보고 크게 감점(설계 가정).
SLOPE_PENALTY = {
    "manual_wheelchair": {"완만한 편": 0, "보통": 1.5, "가파른 편": 4, "기록 없음": 1.5},
    "stroller": {"완만한 편": 0, "보통": 1.2, "가파른 편": 3, "기록 없음": 1.2},
    "electric_wheelchair": {"완만한 편": 0, "보통": 0.5, "가파른 편": 2.5, "기록 없음": 1},
    "senior": {"완만한 편": 0, "보통": 1, "가파른 편": 2.5, "기록 없음": 1},
    "other": {"완만한 편": 0, "보통": 0.5, "가파른 편": 1.5, "기록 없음": 0.5},
}
WALK_M_PER_MIN = 50  # 시속 3km 가정(휠체어·유모차 동행 산책 속도로 잡은 설계 가정)

SLOPE_WORDS = {
    "완만한 편": "길이 대체로 완만해요.",
    "보통": "짧은 오르막·내리막이 있어요. 천천히 가면 괜찮은 편이에요.",
    "가파른 편": "가파른 구간이 있어요. 동행인이 함께 밀어주는 게 좋아요.",
    "기록 없음": "경사 기록이 없어요. 현장 확인이 필요해요.",
}


@lru_cache(maxsize=1)
def load():
    def rd(name):
        return pd.read_csv(PROC / name, encoding="utf-8-sig")
    return {
        "places": rd("places_app.csv"),
        "points": rd("points.csv"),
        "nearby": rd("nearby_checked.csv"),
        "companion": rd("companion.csv"),
        "areas": rd("areas.csv"),
        "medical": rd("medical.csv"),
        "food": rd("food.csv"),
    }


def km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def find_area(text):
    """'애월', '협재리', '중문 쪽', '서귀포' 같은 말에서 동네 좌표를 찾는다."""
    if not text:
        return None
    d = load()["areas"]
    t = re.sub(r"\s|쪽|근처|부근|에서|시내", "", str(text))
    for cand in (t, re.sub(r"(읍|면|동|리)$", "", t)):
        hit = d[d["area"] == cand]
        if len(hit):
            r = hit.iloc[0]
            return {"area": r["area"], "sigungu": r["sigungu"], "lat": float(r["lat"]), "lon": float(r["lon"])}
    if "서귀포" in t:
        return {"area": "서귀포시", "sigungu": "서귀포시", "lat": None, "lon": None}
    if "제주시" in t or t == "제주":
        return {"area": "제주시", "sigungu": "제주시", "lat": None, "lon": None}
    return None


def minutes_for(course_m):
    return int(round(course_m / WALK_M_PER_MIN / 5.0) * 5) or 5


def _companion(place, user_type):
    c = load()["companion"]
    key = COMPANION_KEY.get(user_type)
    if not key:
        return ""
    hit = c[(c["place"] == place) & (c["user_type"].str.contains(re.escape(key)))]
    return "yes" if len(hit) and hit.iloc[0]["companion_advised"] == "yes" else ""


def access_summary(r, user_type="other"):
    """판정 한 줄 + 확인한 것/못 한 것 목록.
    판정은 Wheelmap처럼 3단계(갈 만해요/도움 있으면/확인 더 필요)로 단순화한 설계 규칙이다(안전 보장 아님)."""
    wheels = user_type in ("manual_wheelchair", "electric_wheelchair", "stroller")
    grade = r["slope_relative"]
    stairs = int(r["route_stairs_points"])
    step = None if pd.isna(r["route_step_max_cm"]) else float(r["route_step_max_cm"])
    long_walk = minutes_for(r["course_m"]) > 60 and int(r["rest_points"]) < 2
    if grade == "기록 없음":
        verdict, color = "확인이 더 필요해요", "gray"
        reason = "이 코스는 경사 기록이 없어요."
    elif grade == "가파른 편" or (wheels and (stairs >= 2 or (step or 0) >= 10)) or (user_type == "senior" and (stairs >= 2 or long_walk)):
        verdict, color = "동행인 도움이 있으면 갈 만해요", "orange"
        parts = []
        if grade == "가파른 편":
            parts.append("가파른 구간")
        if stairs:
            parts.append(f"계단 {stairs}곳")
        if wheels and (step or 0) >= 10:
            parts.append(f"턱 {step:g}cm")
        if user_type == "senior" and long_walk:
            parts.append("쉴 곳이 적은 긴 코스")
        reason = ", ".join(parts) + "이(가) 있어요."
    else:
        verdict, color = "갈 만해요", "green"
        reason = "기록된 경사가 완만한 편이고 큰 장벽 기록이 없어요." if grade == "완만한 편" else "짧은 오르막·내리막 정도예요."
    slope_v = r["route_slope_max_deg"]
    checks = [
        {"item": "경사", "status": "기록 없음" if pd.isna(slope_v) else f"가장 가파른 곳 약 {slope_v:g}도 ({grade})",
         "known": not pd.isna(slope_v)},
        {"item": "계단", "status": f"코스 안 {stairs}곳" if stairs else "코스 안 기록 없음", "known": True},
        {"item": "턱", "status": f"가장 높은 턱 {step:g}cm" if step else "수치 기록 없음", "known": step is not None},
        {"item": "장애인 화장실", "status": "있음" if r["accessible_toilet"] == "yes" else "확인 안 됨",
         "known": r["accessible_toilet"] == "yes"},
        {"item": "장애인 주차", "status": {"yes": "있음", "no": "없음"}.get(r["accessible_parking"], "확인 안 됨"),
         "known": r["accessible_parking"] in ("yes", "no")},
        {"item": "쉬어 갈 곳", "status": f"{int(r['rest_points'])}곳" if int(r["rest_points"]) else "기록 없음",
         "known": int(r["rest_points"]) > 0},
    ]
    return {"verdict": verdict, "verdict_color": color, "verdict_reason": reason, "checks": checks,
            "source": f"제주데이터허브 무장애여행 정보({r.get('survey', '')}, {r['base_date']} 기준)"}


def recommend_places(user_type="other", area=None, theme=None, need_toilet=False, max_minutes=None, limit=3,
                     origin_lat=None, origin_lon=None):
    """조건에 맞는 장소를 점수로 정렬해 추천한다. origin_lat/lon(현재 위치)이 있으면 동네 이름보다 우선한다."""
    d = load()
    p = d["places"].copy()
    user_type = user_type if user_type in USER_TYPES else "other"
    if origin_lat is not None and origin_lon is not None:
        loc = {"area": "현재 위치", "sigungu": None, "lat": float(origin_lat), "lon": float(origin_lon)}
    else:
        loc = find_area(area)
    rows = []
    for _, r in p.iterrows():
        score, why, warn = 0.0, [], []
        grade = r["slope_relative"]
        score += SLOPE_PENALTY[user_type].get(grade, 1)
        stairs = int(r["route_stairs_points"])
        blocked = int(r["route_blocked_points"])
        score += min(stairs, 3) * (0.8 if user_type in ("manual_wheelchair", "stroller") else 0.5)
        score += min(blocked, 3) * 0.6
        if stairs:
            warn.append(f"코스 중 계단이 있는 곳 {stairs}군데(옆길이나 우회로가 있는지 확인)")
        toilet = r["accessible_toilet"] == "yes"
        if need_toilet and not toilet:
            score += 3
        if toilet:
            score -= 0.5
            why.append("코스 안에 장애인 화장실이 있어요")
        if theme:  # 사용자가 말한 분위기는 경사보다 먼저 맞춘다(안 맞으면 크게 감점)
            if isinstance(r["themes"], str) and theme in r["themes"]:
                why.append(f"'{theme}' 분위기 장소예요")
            else:
                score += 6
        dist = None
        if loc and loc.get("lat") is not None:
            dist = km(loc["lat"], loc["lon"], r["start_lat"], r["start_lon"])
            score += dist / 3  # 사용자가 말한 동네에서 10km 멀어지면 약 3점 감점
        elif loc and loc.get("sigungu") and r["sigungu"] != loc["sigungu"]:
            continue  # '서귀포', '제주시'처럼 시를 말하면 그 시 안에서만 찾는다
        mins = minutes_for(r["course_m"])
        if max_minutes and mins > max_minutes:
            score += 2
        if r["accessible_parking"] == "yes":
            why.append("장애인 주차구역이 있어요")
        if int(r["rest_points"]) >= 2:
            why.append(f"쉬어 갈 곳이 {int(r['rest_points'])}군데 있어요")
        rows.append({
            "place": r["place"],
            "where": f"{r['sigungu']} {r['dong']}",
            "score": round(score, 2),
            "slope_level": grade,
            "slope_say": SLOPE_WORDS.get(grade, ""),
            "route_slope_max_deg": None if pd.isna(r["route_slope_max_deg"]) else float(r["route_slope_max_deg"]),
            "course_m": int(r["course_m"]),
            "minutes": mins,
            "distance_km": None if dist is None else round(dist, 1),
            "accessible_toilet": toilet,
            "accessible_parking": r["accessible_parking"],
            "companion_advised": _companion(r["place"], user_type) == "yes",
            "good_points": why[:3],
            "watch_out": warn,
            "themes": r["themes"],
            "lat": float(r["start_lat"]),
            "lon": float(r["start_lon"]),
            "base_date": r["base_date"],
            **access_summary(r, user_type),
        })
    rows.sort(key=lambda x: (x["score"], x["place"]))
    return {
        "user_type": USER_TYPES[user_type],
        "area_understood": loc["area"] if loc else None,
        "results": rows[: max(1, min(int(limit), 5))],
        "note": "무장애 현장 정보는 2021년 조사 자료예요. 방문 전 확인을 권장해요.",
    }


def match_place(text):
    """'사려니숲', '국립박물관'처럼 이름 일부만 말해도 데이터의 장소 이름을 찾는다."""
    if not text:
        return None
    names = load()["places"]["place"].tolist()
    t = re.sub(r"\s", "", str(text))
    if t in names:
        return t
    if find_area(t) or len(t) < 3:  # '서귀포', '애월' 같은 동네 이름은 장소 이름으로 보지 않는다
        return None
    hits = [n for n in names if t in n or (len(t) >= 3 and n.replace("제주", "") in t)]
    return sorted(hits, key=len)[0] if hits else None


def resolve_anchor(name):
    """'근처'의 기준이 되는 이름을 좌표로 바꾼다. 나들이 장소, 그다음 식당·카페 이름."""
    if not name:
        return None
    d = load()
    pl = match_place(name)
    if pl:
        r = d["places"][d["places"]["place"] == pl].iloc[0]
        return (float(r["start_lat"]), float(r["start_lon"]), pl)
    loc = find_area(name)
    if loc:  # 동네 이름이면 동네 중심 좌표(가게 이름으로 해석하지 않는다)
        return (loc["lat"], loc["lon"], loc["area"]) if loc.get("lat") is not None else None
    key = re.sub(r"\s", "", str(name))
    for df in (d["nearby"], d["food"]):
        if "lat" not in df.columns:
            continue
        names = df["name"].fillna("").str.replace(r"\s", "", regex=True)
        hit = df[(names == key) & df["lat"].notna()]
        if hit.empty and len(key) >= 4:  # 이름 일부 일치는 4글자 이상일 때만
            hit = df[names.str.contains(re.escape(key)) & df["lat"].notna()]
        if len(hit):
            r = hit.iloc[0]
            return (float(r["lat"]), float(r["lon"]), str(r["name"]))
    return None


def get_place_detail(place, user_type="other"):
    """장소의 코스 흐름(출발→주의 지점→쉼터·화장실)을 순서대로 돌려준다."""
    d = load()
    place = match_place(place) or place
    pl = d["places"][d["places"]["place"] == place]
    if pl.empty:
        return {"error": f"'{place}' 장소를 찾지 못했어요."}
    r = pl.iloc[0]
    pts = d["points"][(d["points"]["place"] == place)].copy()
    pts["order"] = pd.to_numeric(pts["order"], errors="coerce")
    pts = pts.sort_values("order")
    route = pts[pts["on_route"] == "Y"]
    steps, acc, prev = [], 0.0, None
    for _, p in route.iterrows():
        if prev is not None:
            acc += km(prev[0], prev[1], p["lat"], p["lon"]) * 1000
        prev = (p["lat"], p["lon"])
        flags = []
        if p.get("slope_max_deg") == p.get("slope_max_deg") and p.get("slope_max_deg") != "" and pd.notna(p.get("slope_max_deg")):
            flags.append(f"경사 약 {p['slope_max_deg']:g}도")
        if pd.notna(p.get("step_max_cm")):
            flags.append(f"턱 {p['step_max_cm']:g}cm")
        if p.get("stairs") == "yes":
            flags.append("계단")
        if p.get("blocked") == "yes":
            flags.append("진입 어려움")
        if p.get("needs_help") == "yes":
            flags.append("도움 필요")
        if p.get("accessible_toilet") == "yes":
            flags.append("장애인 화장실")
        if p.get("accessible_parking") == "yes":
            flags.append("장애인 주차")
        steps.append({"at_m": int(round(acc, -1)), "label": p["label"], "text": p["text"], "flags": flags,
                      "lat": float(p["lat"]), "lon": float(p["lon"])})
    important = [s for s in steps if s["flags"]]
    return {
        "place": place,
        "where": f"{r['sigungu']} {r['dong']}",
        "course_m": int(r["course_m"]),
        "minutes": minutes_for(r["course_m"]),
        "slope_level": r["slope_relative"],
        "slope_say": SLOPE_WORDS.get(r["slope_relative"], ""),
        "companion_advised": _companion(place, user_type) == "yes",
        **access_summary(r, user_type),
        "key_points": important[:12],
        "all_points": steps,
        "base_date": r["base_date"],
        "source": "제주데이터허브 무장애여행 위치정보(제주특별자치도)",
    }


def find_nearby_help(place, kinds=("약국", "병·의원", "응급실")):
    """장소 출발점에서 가장 가까운 약국·병의원·응급실."""
    d = load()
    anchor = resolve_anchor(place)
    if anchor is None:
        return {"error": f"'{place}' 위치를 찾지 못했어요."}
    lat, lon, place = anchor
    med = d["medical"].copy()
    # 나들이 중 급할 때 갈 곳만 남긴다(치과·성형·피부과·검사 의원 제외)
    med = med[~med["detail"].fillna("").str.contains("치과|성형|피부|방사선|한의원|한방|요양")]
    med["km"] = [km(lat, lon, a, b) for a, b in zip(med["lat"], med["lon"])]
    out = {}
    for k in kinds:
        top = med[med["kind"] == k].nsmallest(2 if k != "응급실" else 1, "km")
        out[k] = [{"name": t["name"], "km": round(t["km"], 1), "address": t["address"],
                   "phone": "" if pd.isna(t["phone"]) else str(t["phone"]), "detail": "" if pd.isna(t["detail"]) else t["detail"],
                   "source": t["source"]} for _, t in top.iterrows()]
    return {"place": place, "help": out, "note": "직선거리 기준이에요. 응급 시에는 119에 먼저 연락하세요."}


def check_nearby_places(place, category=None, wheelchair_only=False, limit=6):
    """장소 주변 식당·카페·숙소. 휠체어 진입 표시와 2025년 영업 확인 결과를 함께 준다."""
    d = load()
    n = d["nearby"][d["nearby"]["place"] == place].copy()
    if category:
        n = n[n["category"].str.contains(category.split("/")[0], na=False)]
    n = n[n["category"] != "주변 관광지"]
    if wheelchair_only:
        n = n[n["wheelchair_entry"] == "yes"]
    order = {"영업 확인": 0, "확인 안 됨": 1, "폐업 기록": 2}
    n["o"] = n["open_status"].map(order).fillna(3)
    n["w"] = (n["wheelchair_entry"] != "yes").astype(int)
    n = n.sort_values(["o", "w", "distance_km"])
    return {
        "place": place,
        "items": [{"category": r["category"], "name": r["name"], "km": r["distance_km"],
                   "phone": "" if pd.isna(r["phone"]) else str(r["phone"]),
                   "wheelchair_entry": r["wheelchair_entry"] == "yes",
                   "accessible_toilet": r["accessible_toilet"] == "yes",
                   "open_status": r["open_status"]} for _, r in n.head(int(limit)).iterrows()],
        "note": "휠체어 진입·화장실 정보는 2021년 조사, 영업 여부는 2025년 음식점·상가 자료로 확인했어요.",
    }


FOOD_KINDS = {
    # 사용자 말 -> (상가 업종, 가게 이름에 자주 들어가는 말)
    "해산물": (["횟집", "일식 회/초밥", "해산물 구이/찜", "복 요리 전문"],
             r"해녀|해물|회|갈치|고등어|전복|성게|물회|수산|옥돔|보말|조개|문어|해산"),
    "흑돼지·고기": (["돼지고기 구이/찜", "소고기 구이/찜", "닭/오리고기 구이/찜"], r"흑돼지|돼지|고기|갈비"),
    "국수": (["국수/칼국수", "냉면/밀면"], r"국수|면"),
    "한식·백반": (["백반/한정식", "국/탕/찌개류", "기타 한식 음식점"], r"식당|밥|정식"),
    "카페": (["카페", "빵/도넛", "아이스크림/빙수"], r"카페|커피|베이커리"),
    "분식·간단히": (["김밥/만두/분식", "토스트/샌드위치/샐러드", "버거"], r"김밥|분식"),
}


def _food_match(kind, food_type, name):
    """업종을 알면 업종으로만, 업종을 모르면(2021 조사 가게 일부) 가게 이름으로 판단한다."""
    if not kind or kind not in FOOD_KINDS:
        return True
    types, pat = FOOD_KINDS[kind]
    if isinstance(food_type, str) and food_type:
        return food_type in types
    return bool(re.search(pat, str(name)))


def search_food(food_kind=None, area=None, place=None, wheelchair_only=False, limit=5, origin_lat=None, origin_lon=None):
    """식당·카페 찾기. 휠체어 진입 정보가 있는 가게(2021 무장애 조사)를 먼저, 부족하면 일반 가게(2025 상가)로 채운다."""
    d = load()
    center = None
    anchor_missing = None
    if place:
        center = resolve_anchor(place)
        if center is None:
            anchor_missing = place
    city = None
    if center is None and origin_lat is not None and origin_lon is not None:
        center = (float(origin_lat), float(origin_lon), "현재 위치")
    if center is None and area:
        loc = find_area(area)
        if loc and loc.get("lat") is not None:
            center = (loc["lat"], loc["lon"], loc["area"])
        elif loc:  # '서귀포', '제주시'처럼 시 단위로 말한 경우
            city = loc["sigungu"]
    radius = 3 if place else 6        # 일반 가게 반경(km)
    access_radius = 5 if place else 10  # 휠체어 정보가 있는 가게는 귀해서 더 넓게

    near = d["nearby"]
    near = near[near["category"].isin(["음식점", "카페/편의점"]) & (near["open_status"] != "폐업 기록")]
    near = near[[_food_match(food_kind, t, n) for t, n in zip(near["food_type"], near["name"])]]
    near = near.drop_duplicates("name")
    if city:
        near = near[near["address"].fillna("").str.contains(city)]
    acc = []
    for _, r in near.iterrows():
        if pd.isna(r.get("lat")):
            continue
        dist = km(center[0], center[1], r["lat"], r["lon"]) if center else None
        if center and dist > access_radius:
            continue
        acc.append({"name": r["name"], "food_type": r["food_type"] if isinstance(r["food_type"], str) else r["category"],
                    "km": None if dist is None else round(dist, 1), "phone": "" if pd.isna(r["phone"]) else str(r["phone"]),
                    "address": r["address"], "wheelchair_entry": r["wheelchair_entry"] == "yes",
                    "accessible_toilet": r["accessible_toilet"] == "yes", "open_status": r["open_status"],
                    "access_info": "2021 무장애 조사", "lat": float(r["lat"]), "lon": float(r["lon"])})
    if wheelchair_only:
        acc = [a for a in acc if a["wheelchair_entry"]]
    acc.sort(key=lambda a: (not a["wheelchair_entry"], a["open_status"] != "영업 확인", a["km"] or 0))

    others = []
    if len(acc) < limit and center and not wheelchair_only:
        f = d["food"]
        f = f[[_food_match(food_kind, t, n) for t, n in zip(f["food_type"], f["name"])]] if food_kind else f
        f = f.assign(km=[km(center[0], center[1], a, b) for a, b in zip(f["lat"], f["lon"])])
        f = f[f["km"] <= radius].nsmallest(limit * 2, "km")
        seen = {a["name"] for a in acc}
        for _, r in f.iterrows():
            if r["name"] in seen:
                continue
            others.append({"name": r["name"], "food_type": r["food_type"], "km": round(r["km"], 1), "phone": "",
                           "address": r["address"], "wheelchair_entry": None, "accessible_toilet": None,
                           "open_status": "영업 중(2025 상가 자료)", "access_info": "휠체어 정보 없음",
                           "lat": float(r["lat"]), "lon": float(r["lon"])})
    # 같이나들이는 '갈 수 있는 곳'을 답한다: 접근성 확인된 가게만 주 결과, 나머지는 따로 분리
    if anchor_missing and center is None and not city:
        return {"food_kind": food_kind, "around": anchor_missing, "items": [], "unverified": [],
                "with_access_info": 0, "anchor_not_found": True,
                "note": f"'{anchor_missing}' 위치를 찾지 못했어요. 동네 이름(예: 서귀포 시내, 중문)으로 말해 주세요."}
    return {
        "food_kind": food_kind, "around": center[2] if center else (city or "제주 전체"),
        "items": acc[: int(limit)],
        "unverified": others[:3],
        "with_access_info": len(acc[: int(limit)]),
        "note": "휠체어 진입은 2021년 무장애 조사 결과예요. 가기 전 전화로 한 번 더 확인해 주세요.",
    }


CALL_QUESTIONS = {
    "manual_wheelchair": ["입구에 턱이나 계단이 있나요?", "휠체어가 들어갈 만큼 문이 넓은가요?", "장애인 화장실이 있나요?", "가까운 곳에 주차할 수 있나요?"],
    "electric_wheelchair": ["입구에 턱이나 계단이 있나요?", "전동 휠체어가 들어갈 만큼 통로가 넓은가요?", "장애인 화장실이 있나요?"],
    "stroller": ["유모차를 끌고 들어갈 수 있나요?", "기저귀 갈 곳이나 수유실이 있나요?", "아기 의자가 있나요?"],
    "senior": ["입구에 계단이 많은가요?", "의자에 앉는 자리가 있나요(좌식만 있는지)?", "화장실이 가까운가요?"],
    "other": ["입구에 턱이나 계단이 있나요?", "화장실이 있나요?"],
}


def call_questions(user_type="other"):
    """가기 전 전화로 물어볼 질문(이동 유형별). 오래된 정보의 한계를 사용자가 직접 확인할 수 있게 돕는다."""
    return CALL_QUESTIONS.get(user_type, CALL_QUESTIONS["other"])


# ---------- 날씨(외부: Open-Meteo, 키 불필요) ----------
# 판단 기준은 설계 가정이다: 강수확률 60% 이상 또는 강수량 5mm 이상이면 '비', 최대풍속 9m/s 이상이면 '강풍'.
RAIN_PROB, RAIN_MM, WIND_MS = 60, 5.0, 9.0
SLIPPERY = ("잔디", "흙", "자갈", "모래", "비포장", "판석", "데크", "야자매트")
_WX_CACHE = {}


def _forecast(lat, lon):
    import json
    import time
    import urllib.request
    key = (round(lat, 2), round(lon, 2))
    hit = _WX_CACHE.get(key)
    if hit and time.time() - hit[0] < 1800:  # 30분 캐시
        return hit[1]
    url = ("https://api.open-meteo.com/v1/forecast?latitude=%.4f&longitude=%.4f"
           "&daily=weather_code,precipitation_probability_max,precipitation_sum,wind_speed_10m_max,"
           "temperature_2m_max,temperature_2m_min&wind_speed_unit=ms&timezone=Asia%%2FSeoul"
           "&forecast_days=7&past_days=1" % (lat, lon))
    with urllib.request.urlopen(url, timeout=8) as r:
        data = json.load(r)["daily"]
    _WX_CACHE[key] = (time.time(), data)
    return data


def _pick_day(days, when):
    import datetime as dt
    today = dt.date.today()
    names = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}
    w = str(when or "오늘")
    if "내일" in w:
        target = today + dt.timedelta(days=1)
    elif "모레" in w:
        target = today + dt.timedelta(days=2)
    elif "주말" in w or "토" in w:
        target = today + dt.timedelta(days=(5 - today.weekday()) % 7)
    elif re.match(r"\d{4}-\d{2}-\d{2}", w):
        target = dt.date.fromisoformat(w[:10])
    else:
        target = next((today + dt.timedelta(days=(v - today.weekday()) % 7) for k, v in names.items() if w.startswith(k + "요")), today)
    t = target.isoformat()
    return days.index(t) if t in days else None


def get_weather(place=None, area=None, when="오늘"):
    """장소(또는 동네) 날씨 예보와 접근성 관점의 주의사항. 인터넷이 안 되면 available=False."""
    d = load()
    lat = lon = None
    name = place or area or "제주시"
    surfaces, themes = "", ""
    if place:
        pl = d["places"][d["places"]["place"] == place]
        if len(pl):
            r = pl.iloc[0]
            lat, lon = float(r["start_lat"]), float(r["start_lon"])
            surfaces, themes = str(r.get("rough_surface") or ""), str(r.get("themes") or "")
    if lat is None:
        loc = find_area(area or "제주시") or {}
        lat, lon = loc.get("lat") or 33.4996, loc.get("lon") or 126.5312
    try:
        w = _forecast(lat, lon)
    except Exception:
        return {"available": False, "note": "지금은 날씨를 불러올 수 없어요. 출발 전 날씨를 꼭 확인해 주세요."}
    i = _pick_day(w["time"], when)
    if i is None:
        return {"available": False, "note": "7일 안의 날씨만 볼 수 있어요."}
    prob, mm, wind = w["precipitation_probability_max"][i], w["precipitation_sum"][i], w["wind_speed_10m_max"][i]
    prev_mm = w["precipitation_sum"][i - 1] if i > 0 else 0
    rain = (prob or 0) >= RAIN_PROB or (mm or 0) >= RAIN_MM
    tips = []
    if rain:
        tips.append("비 예보가 있어요. 실내 장소를 고르거나 우비·바퀴 닦을 수건을 챙기세요.")
    slippery = [s for s in SLIPPERY if s in surfaces]
    if (rain or (prev_mm or 0) >= RAIN_MM) and slippery:
        tips.append(f"코스에 {', '.join(slippery)} 길이 있어 비 온 뒤 미끄러울 수 있어요.")
    if (wind or 0) >= WIND_MS:
        tips.append("바람이 강해요." + (" 해안·방파제 구간은 휠체어·유모차가 밀릴 수 있어 조심하세요." if "바다" in themes else ""))
    return {
        "available": True, "where": name, "date": w["time"][i],
        "rain_chance": prob, "rain_mm": mm, "wind_ms": wind,
        "temp": f"{w['temperature_2m_min'][i]:.0f}~{w['temperature_2m_max'][i]:.0f}°C",
        "is_rainy": rain, "tips": tips,
        "source": "Open-Meteo 예보(외부 서비스)",
    }


def kakao_route_link(name, lat, lon):
    return f"https://map.kakao.com/link/to/{name},{lat},{lon}"
