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
    "pregnant": "임산부",
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
    "pregnant": {"완만한 편": 0, "보통": 1, "가파른 편": 2.5, "기록 없음": 1},
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
    places = rd("places_app.csv")
    if (PROC / "place_contacts.csv").exists():  # 카카오에서 미리 찾은 장소 전화번호·링크
        c = rd("place_contacts.csv")[["place", "phone", "place_url"]]
        places = places.merge(c, on="place", how="left")
    return {
        "places": places,
        "points": rd("points.csv"),
        "nearby": rd("nearby_checked.csv"),
        "companion": rd("companion.csv"),
        "areas": rd("areas.csv"),
        "medical": rd("medical.csv"),
        "food": rd("food.csv"),
        # 제주데이터허브 OpenAPI로 받은 자료(scripts/07_hub_api.py). 없으면 빈 표로 두고 기능만 빠진다.
        "bus": rd("bus_stops.csv") if (PROC / "bus_stops.csv").exists() else pd.DataFrame(),
        "pharmacy": rd("pharmacy_status.csv") if (PROC / "pharmacy_status.csv").exists() else pd.DataFrame(),
        "toilets": rd("toilets.csv") if (PROC / "toilets.csv").exists() else pd.DataFrame(),
        "tour": rd("tour_places.csv") if (PROC / "tour_places.csv").exists() else pd.DataFrame(),
    }


BUS_SOURCE = "제주데이터허브 버스 정류소 기본 정보"
PHARMACY_SOURCE = "제주데이터허브 약국 정보(2025-08)"


def _road(address):
    """'제주특별자치도 제주시 애월읍 애월로 12' -> '애월로'. 도로명이 없으면 ''."""
    m = re.search(r"(?:시|군)\s+(?:\S+[읍면]\s+)?(\S+?(?:로|길))(?:\s|\d|,|$)", str(address))
    return m.group(1) if m else ""


@lru_cache(maxsize=1)
def _pharmacy_index():
    """약국 이름(공백 제거) -> [(도로명, 영업상태)]. 상가 정보에는 영업 상태가 없어서 약국 정보 API로 보탠다."""
    ph = load()["pharmacy"]
    idx = {}
    if ph.empty:
        return idx
    for name, status, addr in zip(ph["name"], ph["open_status"].fillna(""), ph["address_doro"].fillna("")):
        idx.setdefault(re.sub(r"\s", "", str(name)), []).append((_road(addr), status))
    return idx


def pharmacy_status(name, address):
    """'영업' / '폐업' / ''(확인 안 됨). 이름이 같고 도로명이 같은(또는 그 이름이 하나뿐인) 기록으로 판단한다."""
    recs = _pharmacy_index().get(re.sub(r"\s", "", str(name)))
    if not recs:
        return ""
    road = _road(address)
    same = [s for r, s in recs if road and r == road] or ([s for _, s in recs] if len(recs) == 1 else [])
    if not same:
        return ""
    return "영업" if any(s.startswith("영업") for s in same) else "폐업"


def nearest_bus_stops(lat, lon, limit=2, max_km=1.0):
    """좌표에서 가까운 버스 정류소. 같은 이름의 양방향 정류소는 더 가까운 하나만 남긴다."""
    bus = load()["bus"]
    if bus.empty or lat is None or lon is None:
        return []
    # 대략 1.5km 상자 안에서만 거리를 잰다(4천여 곳 전부를 재지 않게)
    near = bus[(bus["lat"] - lat).abs().lt(0.014) & (bus["lon"] - lon).abs().lt(0.017)].copy()
    if near.empty:
        return []
    near["km"] = [km(lat, lon, a, b) for a, b in zip(near["lat"], near["lon"])]
    near = near[near["km"] <= max_km].sort_values("km").drop_duplicates("name")
    out = []
    for _, s in near.head(int(limit)).iterrows():
        m = int(round(s["km"] * 1000, -1))
        out.append({"name": s["name"], "local_info": "" if pd.isna(s["local_info"]) else str(s["local_info"]),
                    "direction": "" if pd.isna(s["direction"]) else str(s["direction"]),
                    "m": m, "walk_min": max(1, round(m / WALK_M_PER_MIN)),
                    "lat": float(s["lat"]), "lon": float(s["lon"])})
    return out


TOUR_SURVEY = "관광공사 무장애 여행 정보"


def is_tour(r):
    return str(r.get("survey", "")) == TOUR_SURVEY


def _txt(v):
    return "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v).strip()


# 성인만 입장하는 곳: 유모차(아기) 가족에게는 추천하지 않고, 다른 가족에게는 주의로 알린다
ADULT_ONLY = {"건강과 성 박물관(제주)", "제주러브랜드"}
ADULT_WORDS = r"성인만 입장|성인 전용|성인들만|19세 이상|미성년자 (?:관람|입장)"


def is_adult_only(r):
    return r["place"] in ADULT_ONLY or bool(re.search(ADULT_WORDS, _txt(r.get("overview"))))


def entry_say(entry, user_type="other"):
    """관광공사 출입 문구는 휠체어 기준으로 적혀 있다. 휠체어가 아닌 가족에게는 같은 사실을 넓게 풀어 쓴다."""
    if user_type in ("manual_wheelchair", "electric_wheelchair"):
        return entry
    return re.sub(r"휠체어로?\s*(?:접근|진입|출입|통과|이동)\s*가능(?:함|합니다)?", "휠체어·유모차도 들어갈 수 있음", entry)


def km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def josa(word, pair):
    """받침에 맞는 조사. josa('턱', '은는') → '턱은', josa('경사', '이가') → '경사가'
    괄호 꼬리는 건너뛰고 앞 글자로 본다: josa('건강과 성 박물관(제주)', '을를') → '…(제주)을'.
    숫자로 끝나면 읽는 소리로 본다: josa('올레 7', '을를') → '올레 7을'(칠), josa('올레 2', '을를') → '올레 2를'(이)."""
    w = str(word).rstrip()
    base = re.sub(r"\s*[\(\[][^()\[\]]*[\)\]]$", "", w).rstrip() or w
    last = base[-1] if base else ""
    hangul = "가" <= last <= "힣"
    digit = last.isdigit() and last.isascii()
    has = (hangul and (ord(last) - 0xAC00) % 28 != 0) or (digit and last in "013678")
    if pair == "으로" and ((hangul and (ord(last) - 0xAC00) % 28 == 8) or (digit and last in "178")):  # ㄹ받침 + 로
        return w + "로"
    a, b = {"은는": ("은", "는"), "이가": ("이", "가"), "을를": ("을", "를"), "과와": ("과", "와"), "으로": ("으로", "로")}[pair]
    return w + (a if has else b)


def join_and(words):
    """['경사', '턱'] → '경사와 턱', ['경사', '턱', '계단'] → '경사, 턱과 계단'"""
    words = [str(x) for x in words if x]
    if len(words) <= 1:
        return "".join(words)
    return ", ".join(words[:-2] + [josa(words[-2], "과와") + " " + words[-1]])


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
    if is_tour(r):
        return _tour_summary(r, user_type)
    grade = r["slope_relative"]
    stairs = int(r["route_stairs_points"])
    step = None if pd.isna(r["route_step_max_cm"]) else float(r["route_step_max_cm"])
    long_walk = minutes_for(r["course_m"]) > 60 and int(r["rest_points"]) < 2
    if grade == "기록 없음":
        verdict, color = "확인이 더 필요해요", "gray"
        reason = "이 코스는 경사 기록이 없어요."
    elif grade == "가파른 편" or (wheels and (stairs >= 2 or (step or 0) >= 10)) or (user_type in ("senior", "pregnant") and (stairs >= 2 or long_walk)):
        verdict, color = "동행인 도움이 있으면 갈 만해요", "orange"
        parts = []
        if grade == "가파른 편":
            parts.append("가파른 구간")
        if stairs:
            parts.append(f"계단 {stairs}곳")
        if wheels and (step or 0) >= 10:
            parts.append(f"턱 {step:g}cm")
        if user_type in ("senior", "pregnant") and long_walk:
            parts.append("쉴 곳이 적은 긴 코스")
        reason = josa(join_and(parts), "이가") + " 있어요."
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


def _say(t):
    """관광공사 문장('~가능함', '~있음')을 말투로: '~가능해요.', '~있어요.'"""
    t = str(t or "").strip().rstrip(".")
    if not t:
        return ""
    for a, b in (("설치되어 있음", "설치돼 있어요"), ("가능함", "가능해요"), ("있음", "있어요"), ("없음", "없어요"), ("불가", "어려워요")):
        if t.endswith(a):
            t = t[: -len(a)] + b
            break
    return t + "."


def _tour_summary(r, user_type="other"):
    """관광공사 무장애 정보(시설 입구·화장실·대여 중심) 판정. 코스 경사 자료가 아님을 이유에 밝힌다."""
    entry = entry_say(_txt(r.get("entry_access")), user_type)
    ok = _txt(r.get("entry_ok"))
    toilet = r["accessible_toilet"] == "yes"
    if ok == "yes":
        verdict, color = "갈 만해요", "green"
        reason = _say(entry) + (" 장애인 화장실도 있어요." if toilet else "")
    elif ok == "no":
        verdict, color = "동행인 도움이 있으면 갈 만해요", "orange"
        reason = "들어가는 길을 미리 확인해 주세요. " + _say(entry)
    else:
        verdict, color = "확인이 더 필요해요", "gray"
        reason = "출입 경로 정보가 없어요."
    rent_w, rent_s = _txt(r.get("wheelchair_rental")), _txt(r.get("stroller_rental"))
    nursing, elev = _txt(r.get("nursing_room")), _txt(r.get("elevator"))
    checks = [
        {"item": "출입 경로", "status": entry or "정보 없음", "known": bool(entry)},
        {"item": "장애인 화장실", "status": "있음" if toilet else "확인 안 됨", "known": toilet},
        {"item": "장애인 주차", "status": "있음" if r["accessible_parking"] == "yes" else "확인 안 됨",
         "known": r["accessible_parking"] == "yes"},
        {"item": "휠체어 대여", "status": rent_w or "정보 없음", "known": bool(rent_w)},
        {"item": "유모차 대여", "status": rent_s or "정보 없음", "known": bool(rent_s)},
        {"item": "수유실", "status": nursing or "정보 없음", "known": bool(nursing)},
        {"item": "엘리베이터", "status": elev or "정보 없음", "known": bool(elev)},
    ]
    return {"verdict": verdict, "verdict_color": color, "verdict_reason": reason, "checks": checks,
            "source": "한국관광공사 무장애 여행 정보(시설 입구·편의시설 기준, 코스 경사 조사는 아님)"}


# 이동 유형별로 특히 쓸모 있는 시설(칸 이름, 가산점). 관광공사 자료의 대여·수유실·엘리베이터, 공통 주차·쉼터
TYPE_BONUS = {
    "manual_wheelchair": (("wheelchair_rental", .4), ("elevator", .3), ("accessible_parking_yes", .3)),
    "electric_wheelchair": (("elevator", .4), ("accessible_parking_yes", .3), ("wheelchair_rental", .1)),
    "stroller": (("stroller_rental", .4), ("nursing_room", .4), ("elevator", .2)),
    "senior": (("accessible_parking_yes", .4), ("wheelchair_rental", .3), ("rest_2", .4)),
    "pregnant": (("nursing_room", .2), ("accessible_parking_yes", .3), ("rest_2", .3)),
}


def _has(r, col):
    if col == "accessible_parking_yes":
        return r.get("accessible_parking") == "yes"
    if col == "rest_2":
        return int(r.get("rest_points") or 0) >= 2
    v = _txt(r.get(col))
    return bool(v) and not re.search(r"없|불가|정보 없음", v)


def recommend_places(user_type="other", area=None, theme=None, need_toilet=False, max_minutes=None, limit=3,
                     origin_lat=None, origin_lon=None, exclude=None, with_evidence=True):
    """조건에 맞는 장소를 점수로 정렬해 추천한다. origin_lat/lon(현재 위치)이 있으면 동네 이름보다 우선한다."""
    d = load()
    p = d["places"].copy()
    user_type = user_type if user_type in USER_TYPES else "other"
    if origin_lat is not None and origin_lon is not None:
        loc = {"area": "현재 위치", "sigungu": None, "lat": float(origin_lat), "lon": float(origin_lon)}
    else:
        loc = find_area(area)
    if exclude:  # '다른 곳'을 원할 때 이미 보여준 장소는 뺀다
        p = p[~p["place"].isin(list(exclude))]
    if user_type == "stroller":  # 아기와 함께 가는 가족에게 성인 전용 장소는 뺀다
        p = p[~p.apply(is_adult_only, axis=1)]
    rows = []
    for _, r in p.iterrows():
        score, why, warn = 0.0, [], []
        grade = r["slope_relative"]
        tour = is_tour(r)
        wheels = user_type in ("manual_wheelchair", "electric_wheelchair", "stroller")
        if tour:  # 코스 경사 대신 출입 경로로 점수
            ok = _txt(r.get("entry_ok"))
            score += 0 if ok == "yes" else ((2.5 if wheels else 1) if ok == "no" else (1.5 if wheels else 0.8))
            if ok == "yes":
                why.append("출입구까지 턱이 없거나 경사로가 있어요")
            if user_type in ("manual_wheelchair", "electric_wheelchair") and _txt(r.get("wheelchair_rental")):
                why.append("휠체어를 빌릴 수 있어요")
            if user_type == "stroller":
                if _txt(r.get("stroller_rental")):
                    why.append("유모차를 빌릴 수 있어요")
                if _txt(r.get("nursing_room")):
                    why.append("수유실이 있어요")
        else:
            score += SLOPE_PENALTY[user_type].get(grade, 1)
            if grade == "완만한 편" and user_type != "other":
                # 길을 따라 경사를 직접 잰 완만한 코스는 입구 정보만 있는 시설보다 믿을 만하다
                score -= 1.0
                why.insert(0, "길 경사를 직접 잰 완만한 코스예요")
            if user_type in ("senior", "pregnant") and minutes_for(r["course_m"]) <= 40:
                score -= 0.3  # 짧게 다녀올 수 있는 코스
            # 같은 점수일 때의 순서: 휠체어는 가장 가파른 곳이 덜한 코스, 어르신·임산부는 짧은 코스부터
            mx = r["route_slope_max_deg"]
            if user_type in ("manual_wheelchair", "electric_wheelchair") and not pd.isna(mx):
                score += float(mx) * 0.03
            if user_type in ("senior", "pregnant"):
                score += minutes_for(r["course_m"]) / 200
        stairs = int(r["route_stairs_points"])
        blocked = int(r["route_blocked_points"])
        score += min(stairs, 3) * (0.8 if user_type in ("manual_wheelchair", "stroller") else 0.5)
        score += min(blocked, 3) * 0.6
        if stairs:
            warn.append(f"코스 중 계단이 있는 곳 {stairs}군데(옆길이나 우회로가 있는지 확인)")
        if is_adult_only(r):
            warn.append("성인만 입장할 수 있는 곳이에요(아이와 함께라면 다른 곳을 골라 주세요)")
            score += 2
        toilet = r["accessible_toilet"] == "yes"
        if need_toilet and not toilet:
            score += 3
        if toilet:
            score -= 0.5
            why.append("장애인 화장실이 있어요")
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
        mins = None if tour else minutes_for(r["course_m"])
        if max_minutes and mins and mins > max_minutes:
            score += 2
        if r["accessible_parking"] == "yes":
            why.append("장애인 주차구역이 있어요")
        if int(r["rest_points"]) >= 2:
            why.append(f"쉬어 갈 곳이 {int(r['rest_points'])}군데 있어요")
        # 함께 가는 분에게 특히 쓸모 있는 시설에 가산점(같은 점수끼리 이름순으로만 정해지지 않게)
        score -= sum(w for col, w in TYPE_BONUS.get(user_type, ()) if _has(r, col))
        rows.append({
            "place": r["place"],
            "where": f"{r['sigungu']} {r['dong']}",
            "score": round(score, 2),
            "slope_level": grade,
            "slope_say": (f"출입: {entry_say(_txt(r.get('entry_access')), user_type)}" if tour and _txt(r.get("entry_access"))
                          else ("출입 경로 정보가 없어요. 가기 전 확인해 주세요." if tour else SLOPE_WORDS.get(grade, ""))),
            "data_kind": "시설(관광공사)" if tour else "코스(제주도 조사)",
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
            "phone": _txt(r.get("phone")), "place_url": _txt(r.get("place_url")),
            "parking": parking_point(r["place"]),
            "overview": _txt(r.get("overview")), "image": _txt(r.get("image")), "homepage": _txt(r.get("homepage")),
            **access_summary(r, user_type),
        })
    rows.sort(key=lambda x: (x["score"], -len(x["good_points"]), x["place"]))
    if rows:  # 1순위 장소에만 '비 오면 대신 갈 실내 장소'(바깥 장소일 때)
        rows[0]["rain_alt"] = rain_alternative(rows[0]["place"], user_type, exclude=[r["place"] for r in rows[:3]])
    rows = rows[: max(1, min(int(limit), 5))]
    for x in rows if with_evidence else []:  # 판정 근거는 보여줄 장소에만 붙인다
        x["evidence"] = place_evidence(x["place"])
    return {
        "user_type": USER_TYPES[user_type],
        "area_understood": loc["area"] if loc else None,
        "results": rows,
        "note": "코스 정보는 제주도 2020~2021년 조사, 시설 정보는 한국관광공사 자료예요. 방문 전 확인을 권장해요.",
    }


def match_place(text):
    """'사려니숲', '국립박물관'처럼 이름 일부만 말해도 데이터의 장소 이름을 찾는다."""
    if not text:
        return None
    names = load()["places"]["place"].tolist()
    if str(text) in names:
        return str(text)
    bare = {re.sub(r"\s", "", n): n for n in names}  # 관광공사 장소처럼 이름에 띄어쓰기가 있어도 찾는다
    t = re.sub(r"\s", "", str(text))
    if t in bare:
        return bare[t]
    if find_area(t) or len(t) < 3:  # '서귀포', '애월' 같은 동네 이름은 장소 이름으로 보지 않는다
        return None
    if sum(b.endswith(t) for b in bare) >= 2:  # '해안길', '박물관'처럼 여러 장소 이름의 꼬리는 종류 이름이다
        return None
    hits = [n for b, n in bare.items() if t in b or (len(t) >= 3 and b.replace("제주", "") in t)]
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
    key = re.sub(r"\s", "", str(name))
    shops = [df for df in (d["nearby"], d["food"]) if "lat" in df.columns]

    def shop_hit(exact):
        for df in shops:
            names = df["name"].fillna("").str.replace(r"\s", "", regex=True)
            mask = (names == key) if exact else names.str.contains(re.escape(key))
            hit = df[mask & df["lat"].notna()]
            if len(hit):
                r = hit.iloc[0]
                return (float(r["lat"]), float(r["lon"]), str(r["name"]))
        return None

    # 1) 가게 이름 정확히 일치 → 2) 동네 이름 → 3) 가게 이름 일부(4글자 이상)
    exact = shop_hit(True)
    if exact:
        return exact
    loc = find_area(name)
    if loc:
        # '서귀포', '제주시'처럼 시 전체만 말하면 기준점을 임의로 정하지 않는다(None)
        return (loc["lat"], loc["lon"], loc["area"]) if loc.get("lat") is not None else None
    return shop_hit(False) if len(key) >= 4 else None


def get_place_detail(place, user_type="other"):
    """장소의 코스 흐름(출발→주의 지점→쉼터·화장실)을 순서대로 돌려준다."""
    d = load()
    place = match_place(place) or place
    pl = d["places"][d["places"]["place"] == place]
    if pl.empty:
        return {"error": f"'{place}' 장소를 찾지 못했어요."}
    r = pl.iloc[0]
    toilets = nearby_toilets(float(r["start_lat"]), float(r["start_lon"]), "accessible", limit=3, max_km=2)
    if is_tour(r):
        return {
            "place": place, "where": f"{r['sigungu']} {r['dong']}", "course_m": 0, "minutes": None,
            "slope_level": "기록 없음", "slope_say": "", "companion_advised": False,
            **access_summary(r, user_type), "key_points": [],
            "all_points": [{"at_m": 0, "label": "입구", "text": entry_say(_txt(r.get("entry_access")), user_type), "flags": [],
                            "lat": float(r["start_lat"]), "lon": float(r["start_lon"])}],
            "toilets_near": toilets, "tel": _txt(r.get("tel")), "base_date": r["base_date"],
            "rain_alt": rain_alternative(place, user_type),
            "bus_stops": nearest_bus_stops(float(r["start_lat"]), float(r["start_lon"])), "bus_source": BUS_SOURCE,
            "data_kind": "시설(관광공사)",
            "evidence": place_evidence(r),
        }
    steps = [{k: (list(v) if k == "flags" else v) for k, v in s.items() if k not in ("on_route", "used")}
             for s in _course_points(place) if s["on_route"]]
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
        "toilets_near": toilets,
        "rain_alt": rain_alternative(place, user_type),
        "bus_stops": nearest_bus_stops(float(r["start_lat"]), float(r["start_lon"])),
        "bus_source": BUS_SOURCE,
        "base_date": r["base_date"],
        "data_kind": "코스(제주도 조사)",
        "evidence": place_evidence(r),
    }


# ---------- 판정 근거(evidence): 판정 뒤에 있는 공공데이터 기록 원문 ----------
COURSE_EVIDENCE_SOURCE = "제주데이터허브 무장애여행 위치정보"
TOUR_EVIDENCE_SOURCE = "한국관광공사 무장애 여행 정보"
# 관광공사 원문 칸 -> 화면에 보일 이름
TOUR_EVIDENCE_FIELDS = [("출입 경로", "출입 경로"), ("출입문", "출입문"), ("화장실", "장애인 화장실"), ("주차", "장애인 주차"),
                        ("엘리베이터", "엘리베이터"), ("휠체어", "휠체어 대여"), ("유모차", "유모차 대여"),
                        ("수유실", "수유실"), ("유아용 의자", "유아용 의자")]
# places_app.csv 에 남아 있는 칸(관광공사 원문 표가 없을 때 대신 쓴다)
TOUR_APP_FIELDS = {"출입 경로": "entry_access", "휠체어": "wheelchair_rental", "유모차": "stroller_rental",
                   "수유실": "nursing_room", "엘리베이터": "elevator"}


def _point_flags(p):
    """조사 지점 한 곳의 표시(경사·턱·계단…)와, 그 지점이 판정에 쓰였는지(경사·계단·턱·막힘 기록)."""
    flags, used = [], False
    if pd.notna(p.get("slope_max_deg")) and _txt(p.get("slope_max_deg")):
        flags.append(f"경사 약 {p['slope_max_deg']:g}도")
        used = True
    if pd.notna(p.get("step_max_cm")):
        flags.append(f"턱 {p['step_max_cm']:g}cm")
        used = True
    if p.get("stairs") == "yes":
        flags.append("계단")
        used = True
    if p.get("blocked") == "yes":
        flags.append("진입 어려움")
        used = True
    if p.get("needs_help") == "yes":
        flags.append("도움 필요")
    if p.get("accessible_toilet") == "yes":
        flags.append("장애인 화장실")
    if p.get("accessible_parking") == "yes":
        flags.append("장애인 주차")
    return flags, used


@lru_cache(maxsize=None)
def _course_points(place):
    """제주도 조사 지점(조사 순서). 코스 위 지점은 출발점에서 걸은 거리(at_m), 코스 옆 지점은 at_m=None.
    캐시된 값이므로 호출한 쪽에서 고치지 않는다(복사해서 쓴다)."""
    pts = load()["points"]
    pts = pts[pts["place"] == place].copy()
    pts["order"] = pd.to_numeric(pts["order"], errors="coerce")
    out, acc, prev = [], 0.0, None
    for _, p in pts.sort_values("order").iterrows():
        on = p["on_route"] == "Y"
        at = None
        if on:
            if prev is not None:
                acc += km(prev[0], prev[1], p["lat"], p["lon"]) * 1000
            prev = (p["lat"], p["lon"])
            at = int(round(acc, -1))
        flags, used = _point_flags(p)
        out.append({"at_m": at, "label": p["label"], "text": p["text"], "flags": tuple(flags),
                    "lat": float(p["lat"]), "lon": float(p["lon"]), "on_route": on, "used": on and used})
    return tuple(out)


@lru_cache(maxsize=1)
def _tour_raw():
    """관광공사 원문 표: 장소 이름 -> 행(dict)."""
    t = load()["tour"]
    if t.empty:
        return {}
    return {str(r["title"]): r for r in t.astype(object).fillna("").to_dict(orient="records")}


def _course_evidence(r):
    pts = _course_points(r["place"])
    used = [s for s in pts if s["used"]]
    rest = sorted((s for s in pts if not s["used"]), key=lambda s: not s["on_route"])  # 코스 위 -> 코스 옆
    items = [{"label": _txt(s["label"]), "text": _txt(s["text"]), "flags": list(s["flags"]), "at_m": s["at_m"],
              "on_route": s["on_route"], "used": s["used"], "lat": s["lat"], "lon": s["lon"]} for s in used + rest]
    summary = (f"이 코스 조사 지점 {len(pts)}곳 확인" + (f" · 판정에 쓴 지점 {len(used)}곳" if used else "")
               if pts else "이 코스의 조사 지점 기록이 없어요")
    return {"kind": "course", "summary": summary, "source": COURSE_EVIDENCE_SOURCE, "survey": _txt(r.get("survey")),
            "base_date": _txt(r.get("base_date")), "used_count": len(used), "items": items}


def _tour_evidence(r):
    raw = _tour_raw().get(str(r["place"]))
    if raw is None:  # 원문 표가 없으면 장소 표에 남은 칸으로
        raw = {col: _txt(r.get(app_col)) for col, app_col in TOUR_APP_FIELDS.items()}
    texts = {col: _txt(raw.get(col)) for col, _ in TOUR_EVIDENCE_FIELDS}
    # 판정은 '출입 경로'(없으면 '출입문') 문구로 했고, 장애인 화장실이 있으면 이유에 함께 적었다
    entry_col = "출입 경로" if texts["출입 경로"] else "출입문"
    used_cols = {entry_col} | ({"화장실"} if r["accessible_toilet"] == "yes" else set())
    items = [{"label": label, "text": texts[col], "flags": [], "at_m": None, "on_route": None,
              "used": col in used_cols, "lat": None, "lon": None}
             for col, label in TOUR_EVIDENCE_FIELDS if texts[col]]
    items.sort(key=lambda x: not x["used"])
    used_n = sum(x["used"] for x in items)
    summary = (f"관광공사 시설 정보 {len(items)}개 항목 확인" + (f" · 판정에 쓴 항목 {used_n}개" if used_n else "")
               if items else "관광공사 시설 정보에 접근성 항목이 없어요")
    return {"kind": "facility", "summary": summary, "source": TOUR_EVIDENCE_SOURCE, "survey": _txt(r.get("survey")),
            "base_date": _txt(r.get("base_date")), "used_count": used_n, "items": items}


def place_evidence(r):
    """판정(갈 만해요 / 동행인 도움 있으면 / 확인 더 필요) 뒤에 있는 공공데이터 기록.
    r: 장소 표의 한 행 또는 장소 이름. 판정에 쓴 기록(used=True)이 앞에 온다. 화면 전용(모델에게는 넘기지 않는다)."""
    if isinstance(r, str):
        pl = load()["places"]
        hit = pl[pl["place"] == r]
        if hit.empty:
            return None
        r = hit.iloc[0]
    return _tour_evidence(r) if is_tour(r) else _course_evidence(r)


def nearby_toilets(lat, lon, need="accessible", limit=2, max_km=3.0):
    """가까운 공중화장실. need: accessible(장애인용) / diaper(기저귀 교환대) / None(전체)."""
    t = load()["toilets"]
    if t.empty:
        return []
    t = t[t["lat"].notna()]
    if need == "accessible":
        t = t[t["accessible"].astype(str).str.lower() == "true"]
    elif need == "diaper":
        t = t[t["diaper"].astype(str).str.lower() == "true"]
    t = t.assign(km=[km(lat, lon, a, b) for a, b in zip(t["lat"], t["lon"])])
    t = t[t["km"] <= max_km].nsmallest(limit, "km")
    return [{"name": r["name"], "km": round(r["km"], 2), "address": _txt(r["address"]),
             "accessible_count": int(r["accessible_count"]), "diaper": str(r["diaper"]).lower() == "true",
             "open": f"{_txt(r['open'])} {_txt(r['open_detail'])}".strip(), "phone": _phone(r["phone"]),
             "lat": float(r["lat"]), "lon": float(r["lon"])} for _, r in t.iterrows()]


HELP_KINDS = ("약국", "병·의원", "응급실")


def find_nearby_help(place=None, kinds=HELP_KINDS, user_type=None, origin_lat=None, origin_lon=None):
    """기준(장소 또는 현재 위치)에서 가장 가까운 약국·병의원·응급실.
    kinds: 물어본 종류만(약국만 물으면 약국만). 시 전체만 말하고 위치가 없으면 기준을 임의로 정하지 않고
    needs_location을 돌려준다(응급실은 그 시의 응급실을 모두 알려 준다)."""
    d = load()
    kinds = [k for k in (kinds or HELP_KINDS) if k in HELP_KINDS] or list(HELP_KINDS)
    if origin_lat is not None and origin_lon is not None:
        anchor = (float(origin_lat), float(origin_lon), "현재 위치")
    else:
        anchor = resolve_anchor(place)
    if anchor is None:
        loc = find_area(place) if place else None
        city = (loc or {}).get("sigungu") if loc and loc.get("lat") is None else None
        if city and kinds == ["응급실"]:
            er = d["medical"][(d["medical"]["kind"] == "응급실") & d["medical"]["address"].fillna("").str.contains(city)]
            items = [{"name": t["name"], "km": None, "address": t["address"],
                      "phone": "" if pd.isna(t["phone"]) else str(t["phone"]), "detail": "", "status": "",
                      "source": t["source"], "lat": float(t["lat"]), "lon": float(t["lon"])} for _, t in er.iterrows()]
            return {"place": city, "help": {"응급실": items}, "bus": [], "bus_source": BUS_SOURCE,
                    "note": f"{city}의 응급실이에요. 응급 시에는 119에 먼저 연락하세요."}
        if city:
            return {"needs_location": True, "city": city,
                    "error": f"{city} 어디 근처에서 찾을까요? 동네·장소 이름을 말하거나 내 위치로 찾을 수 있어요."}
        return {"error": f"'{place}' 위치를 찾지 못했어요."}
    lat, lon, place = anchor
    med = d["medical"].copy()
    # 나들이 중 급할 때 갈 곳만 남긴다(치과·성형·피부과·검사 의원 제외)
    med = med[~med["detail"].fillna("").str.contains("치과|성형|피부|방사선|한의원|한방|요양")]
    med["km"] = [km(lat, lon, a, b) for a, b in zip(med["lat"], med["lon"])]
    # 약국은 약국 정보 API의 영업 상태를 붙이고, 폐업 기록이 있는 곳은 뺀다
    med["status"] = [pharmacy_status(n, a) if k == "약국" else "" for k, n, a in zip(med["kind"], med["name"], med["address"])]
    med = med[med["status"] != "폐업"]
    out = {}
    for k in kinds:
        top = med[med["kind"] == k].nsmallest(2 if k != "응급실" else 1, "km")
        out[k] = [{"name": t["name"], "km": round(t["km"], 1), "address": t["address"],
                   "phone": "" if pd.isna(t["phone"]) else str(t["phone"]), "detail": "" if pd.isna(t["detail"]) else t["detail"],
                   "status": {"영업": "영업 중 확인"}.get(t["status"], ""),
                   "source": t["source"] + (f" · {PHARMACY_SOURCE}" if t["status"] else ""),
                   "lat": float(t["lat"]), "lon": float(t["lon"])} for _, t in top.iterrows()]
    for items in out.values():  # 병원·약국 자료에는 전화번호가 없어 카카오 장소 검색으로 보강
        for it in items:
            if not it["phone"]:
                kp = kakao_place(it["name"], it["lat"], it["lon"], kind="help")
                if kp and kp.get("phone"):
                    it["phone"], it["place_url"] = kp["phone"], kp["place_url"]
    if user_type == "pregnant":  # 임산부: 가까운 산부인과
        ob = d["medical"][d["medical"]["detail"].fillna("").str.contains("산부인과")].copy()
        ob["km"] = [km(lat, lon, a, b) for a, b in zip(ob["lat"], ob["lon"])]
        out["산부인과"] = [{"name": t["name"], "km": round(t["km"], 1), "address": t["address"], "phone": "",
                          "detail": t["detail"], "source": t["source"], "lat": float(t["lat"]), "lon": float(t["lon"])}
                         for _, t in ob.nsmallest(1, "km").iterrows()]
    out["장애인 화장실"] = nearby_toilets(lat, lon, "accessible")
    out["기저귀 교환대"] = nearby_toilets(lat, lon, "diaper", limit=1)
    note = "직선거리 기준이에요. 응급 시에는 119에 먼저 연락하세요. 화장실은 공중화장실 정보(제주특별자치도)예요."
    if not load()["pharmacy"].empty:
        note += " 약국은 약국 정보(영업 상태)로 폐업한 곳을 뺐어요."
    return {"place": place, "help": out, "bus": nearest_bus_stops(lat, lon), "bus_source": BUS_SOURCE, "note": note}


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
SKIP_TYPES = {"일반 유흥 주점", "무도 유흥 주점", "생맥주 전문", "요리 주점", "구내식당"}  # 가족 식사 대상 아님

# 식사 조건: 어르신·아이가 흔히 겪는 불편. 메뉴 자료가 없어 업종·가게 이름으로 '가능성이 높은 곳'을 고른다.
# 의학적 판단이 아니며, 결과에는 항상 "메뉴는 가게에 확인" 안내를 붙인다.
SPICY = r"매운|매콤|불닭|짬뽕|마라|떡볶이|부대|김치찜|닭발|낙지|쭈꾸미|주꾸미|불고기|화끈"
SEAFOOD_TYPES = {"횟집", "일식 회/초밥", "해산물 구이/찜", "복 요리 전문"}
SEAFOOD_NAME = r"해물|해산|회$|횟집|수산|갈치|고등어|전복|해녀|문어|조개|새우|성게|보말|물회|게장|오징어"
DIET_NEEDS = {
    "soft": {"label": "씹기 편한 음식", "say": "이가 불편하거나 씹기 어려울 때",
             "types": {"국수/칼국수"},
             "name": r"죽$|죽집|본죽|전복죽|팥죽|참죽|죽전문|순두부|두부|우동|수제비|칼국수|곰탕|설렁탕|백숙|몸국|국밥|계란찜|연두부",
             "avoid": r"갈비|구이|족발|닭발|곱창|오징어|육포",
             "ask": ["죽이나 부드러운 메뉴가 있나요?", "음식을 잘게 잘라 주시거나 더 익혀 주실 수 있나요?"]},
    "gentle": {"label": "속 편한 음식", "say": "소화가 어렵거나 속이 불편할 때",
               "types": {"국수/칼국수"},
               "name": r"죽$|죽집|본죽|전복죽|팥죽|우동|백숙|곰탕|설렁탕|두부|칼국수|수제비|몸국",
               "avoid": SPICY + r"|튀김|치킨|곱창|막창|삼겹|마라",
               "ask": ["맵지 않고 기름지지 않은 메뉴가 있나요?"]},
    "mild": {"label": "맵지 않은 음식", "say": "아이나 매운 음식을 못 드시는 분",
             "types": {"경양식", "국수/칼국수", "일식 카레/돈가스/덮밥", "토스트/샌드위치/샐러드", "버거", "피자",
                       "파스타/스테이크", "일식 면 요리", "백반/한정식"},
             "name": r"돈가스|돈까스|우동|국수|죽|김밥|오므라이스|카레|덮밥|정식|생선구이",
             "avoid": SPICY,
             "ask": ["맵지 않은 메뉴가 있나요?", "아이용 의자나 식기가 있나요?"]},
    "no_seafood": {"label": "해산물 없는 식당", "say": "해산물 알레르기가 있을 때",
                   "types": None, "name": None, "avoid": SEAFOOD_NAME,
                   "exclude_types": SEAFOOD_TYPES,
                   "ask": ["해산물이 들어가지 않은 메뉴가 있나요?", "조리 도구를 따로 쓰실 수 있나요?"]},
    "low_salt": {"label": "싱겁게 부탁하기 좋은 곳", "say": "짜게 드시면 안 될 때(고혈압 등)",
                 "types": {"백반/한정식", "국수/칼국수"}, "name": r"정식|한정식|백반|죽|두부",
                 "avoid": r"찌개|짬뽕|부대|김치찜|젓갈|게장",
                 "ask": ["간을 싱겁게 해 주실 수 있나요?", "국물을 덜 짜게 해 주실 수 있나요?"]},
    "no_raw": {"label": "날음식 없는 식당", "say": "임신 중 등 날음식·술을 피하고 싶을 때",
               "types": None, "name": None,
               "avoid": r"회$|횟집|물회|육회|생고기|사시미|초밥|스시|게장|생선회|주점|포차|막걸리|호프",
               "exclude_types": {"횟집", "일식 회/초밥", "요리 주점", "생맥주 전문", "복 요리 전문"},
               "ask": ["날음식이 들어가지 않은 메뉴가 있나요?", "완전히 익힌 메뉴로 부탁드릴 수 있나요?"]},
    "kids": {"label": "아이와 먹기 좋은 곳", "say": "어린아이와 함께일 때",
             "types": {"경양식", "일식 카레/돈가스/덮밥", "피자", "버거", "파스타/스테이크", "국수/칼국수", "김밥/만두/분식"},
             "name": r"돈가스|돈까스|키즈|우동|국수|오므라이스|카레|김밥|피자",
             "avoid": SPICY,
             "ask": ["아이 의자가 있나요?", "맵지 않은 아이 메뉴가 있나요?", "유모차를 두고 앉을 자리가 있나요?"]},
}


def _norm_name(x):
    return re.sub(r"\s|\(.*?\)|주식회사|\(주\)|본점$", "", str(x)).lower()


@lru_cache(maxsize=1)
def _wheelchair_names():
    """2021 무장애 조사에서 휠체어 진입이 확인된 가게 이름(정규화). 2025 상가 가게에 배지로 붙인다."""
    n = load()["nearby"]
    yes = n[(n["wheelchair_entry"] == "yes") & (n["open_status"] != "폐업 기록")]
    return {_norm_name(x): str(p) for x, p in zip(yes["name"], yes["place"])}


@lru_cache(maxsize=1)
def _tour_restaurants():
    """관광공사 무장애 정보가 있는 음식점: 이름 -> (입구 접근 가능 여부, 출입 문구, 아기 의자 문구)."""
    t = load()["tour"]
    if t.empty:
        return {}
    t = t[t["type"] == "음식점"].astype(object).fillna("")
    out = {}
    for _, r in t.iterrows():
        entry = f"{r['출입 경로']} {r['출입문']}".strip()
        ok = bool(re.search(r"턱이 없|턱 없|단차가 없|단차 없|경사로|휠체어 접근 가능|평지", entry)) and not re.search(r"불가|어려", entry)
        out[_norm_name(r["title"])] = (ok, entry, str(r["유아용 의자"]))
    return out


_KAKAO_CACHE = {}


def clean_name(name):
    """상가 자료의 '상호;다른 이름' 형식에서 앞 이름만 쓴다."""
    return re.split(r"\s*;\s*", str(name))[0].strip() or str(name)


KAKAO_GROUPS = {"food": ("FD6", "CE7"), "help": ("HP8", "PM9")}  # 음식점·카페 / 병원·약국


def kakao_place(name, lat, lon, kind="food"):
    """카카오 키워드 검색으로 가게 전화번호·카카오맵 링크를 찾는다(키 없거나 실패하면 None).
    같은 종류(식당·카페 또는 병원·약국)이고 이름이 맞는 곳만 쓴다. 이름 앞 글자만 같은 다른 업종(예: 같은 이름의 충전소)은 버린다."""
    import json
    import os
    import urllib.parse
    import urllib.request
    key = os.getenv("KAKAO_REST_KEY")
    if not key:
        try:
            from dotenv import dotenv_values
            key = dotenv_values(PROC.parents[1] / ".env").get("KAKAO_REST_KEY")
        except Exception:
            key = None
    if not key:
        return None
    name = clean_name(name)
    ck = (name, round(lat, 3), round(lon, 3), kind)
    if ck in _KAKAO_CACHE:
        return _KAKAO_CACHE[ck]
    url = "https://dapi.kakao.com/v2/local/search/keyword.json?" + urllib.parse.urlencode(
        {"query": name, "x": lon, "y": lat, "radius": 300, "sort": "distance"})
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"Authorization": "KakaoAK " + key}), timeout=4) as r:
            docs = json.loads(r.read().decode("utf-8"))["documents"]
        groups = KAKAO_GROUPS.get(kind, ())
        want = _norm_name(name)
        same_kind = [d for d in docs if not groups or d.get("category_group_code") in groups]
        # 1) 이름이 똑같은 곳 → 2) 한쪽 이름이 다른 쪽을 포함하는 곳(지점명 차이) → 3) 앞 세 글자가 같은 곳
        hit = (next((d for d in same_kind if _norm_name(d["place_name"]) == want), None)
               or next((d for d in same_kind if want in _norm_name(d["place_name"]) or _norm_name(d["place_name"]) in want), None)
               or next((d for d in same_kind if _norm_name(d["place_name"])[:3] == want[:3]), None))
        res = {"phone": hit["phone"], "place_url": hit["place_url"], "category": hit["category_name"],
               "name": hit["place_name"]} if hit else None
    except Exception:
        return None  # 연결 실패는 기억하지 않는다(다음에 다시 찾는다)
    _KAKAO_CACHE[ck] = res
    return res


def _kind_ok(kind, food_type, name):
    if not kind or kind not in FOOD_KINDS:
        return True
    types, pat = FOOD_KINDS[kind]
    return (isinstance(food_type, str) and food_type in types) or (not isinstance(food_type, str) and bool(re.search(pat, str(name))))


def _diet_score(needs, food_type, name):
    """식사 조건에 맞으면 (점수, 이유), 피해야 하면 None."""
    score, why = 0, []
    for k in needs or []:
        rule = DIET_NEEDS.get(k)
        if not rule:
            continue
        if rule.get("exclude_types") and food_type in rule["exclude_types"]:
            return None
        if rule.get("avoid") and re.search(rule["avoid"], str(name)):
            return None
        hit_name = rule.get("name") and re.search(rule["name"], str(name))
        hit_type = rule.get("types") and food_type in rule["types"]
        if hit_name:
            score += 2
            why.append(f"{rule['label']}: 가게 이름에 '{hit_name.group(0)}'")
        elif hit_type:
            score += 1
            why.append(f"{rule['label']}: 업종이 {food_type}")
        elif rule.get("types") or rule.get("name"):
            return None  # 조건에 맞는 근거가 없으면 뺀다(해산물 제외처럼 '피하기'만 있는 조건은 통과)
    return score, why


# 일반 손님이 갈 수 없는 곳(구내식당, 기관·단체 사무실 이름)
NOT_RESTAURANT = r"구내식당|구내|운동본부|관리사무소|사무소|직업재활|기숙사|급식|연수원|노인회|복지관|교회|성당|어린이집"


def _phone(x):
    """전화번호 표기 정리: 647602052.0 → 064-760-2052"""
    t = _txt(x)
    if not t:
        return ""
    if re.fullmatch(r"\d+(\.0)?", t):
        n = t.split(".")[0]
        n = n if n.startswith("0") else "0" + n
        if len(n) == 9:  # 0XX-XXX-XXXX 지역번호 2자리(02)
            return f"{n[:2]}-{n[2:5]}-{n[5:]}"
        if len(n) == 10:
            return f"{n[:3]}-{n[3:6]}-{n[6:]}" if not n.startswith("02") else f"{n[:2]}-{n[2:6]}-{n[6:]}"
        if len(n) == 11:
            return f"{n[:3]}-{n[3:7]}-{n[7:]}"
        return n
    return t


def search_food(food_kind=None, area=None, place=None, diet_needs=None, prefer_wheelchair=False,
                wheelchair_only=False, limit=5, origin_lat=None, origin_lon=None, radius_km=None,
                avoid_upstairs=False):
    """제주 식당·카페 찾기(2025 상가 자료 약 1만 9천 곳).
    - 식사 조건(diet_needs: soft, gentle, mild, no_seafood, low_salt, kids)으로 고르고
    - 2021 무장애 조사에서 휠체어 진입이 확인된 가게는 배지로 표시한다(prefer_wheelchair면 앞으로).
    메뉴 자료가 없으므로 업종·가게 이름으로 추정하며, 결과마다 전화 확인 질문을 함께 준다."""
    d = load()
    if diet_needs and "no_seafood" in diet_needs and food_kind == "해산물":
        food_kind = None  # 해산물 알레르기인데 '해산물' 종류를 같이 고르면 결과가 0이 된다
    center, anchor_missing, city = None, None, None
    if place:
        center = resolve_anchor(place)
        if center is None:
            anchor_missing = place
    if center is None and origin_lat is not None and origin_lon is not None:
        center = (float(origin_lat), float(origin_lon), "현재 위치")
    if center is None and area:
        loc = find_area(area)
        if loc and loc.get("lat") is not None:
            center = (loc["lat"], loc["lon"], loc["area"])
        elif loc:
            city = loc["sigungu"]
    if anchor_missing and center is None and not city:
        return {"food_kind": food_kind, "diet_needs": diet_needs or [], "around": anchor_missing, "items": [],
                "unverified": [], "anchor_not_found": True,
                "note": f"'{anchor_missing}' 위치를 찾지 못했어요. 동네 이름(예: 서귀포 시내, 중문)으로 말해 주세요."}

    f = d["food"]
    f = f[~f["name"].astype(str).str.contains(NOT_RESTAURANT, na=False)]  # 구내식당·기관 이름 빼기
    f = f[~f["food_type"].isin(SKIP_TYPES)]
    if city:
        f = f[f["sigungu"] == city]
    f = f[[_kind_ok(food_kind, t, n) for t, n in zip(f["food_type"], f["name"])]]
    wc = _wheelchair_names()
    wheel_first = prefer_wheelchair or wheelchair_only
    if center:
        f = f.assign(km=[km(center[0], center[1], a, b) for a, b in zip(f["lat"], f["lon"])])
        radius = radius_km or (2 if place else 5)
        near = f[f["km"] <= radius]
        if len(near) < limit:  # 가까운 곳이 너무 적으면 반경을 넓힌다
            near = f[f["km"] <= radius * 3]
        if wheel_first:  # 휠체어 진입 확인 가게는 귀해서 반경을 두 배로
            extra = f[(f["km"] <= radius * 2) & f["name"].map(lambda x: _norm_name(x) in wc)]
            near = pd.concat([near, extra]).drop_duplicates(subset=["name", "lat"])
        f = near
    else:
        f = f.assign(km=None)
    items = []
    for _, r in f.iterrows():
        ds = _diet_score(diet_needs, r["food_type"], r["name"])
        if ds is None:
            continue
        tr = _tour_restaurants().get(_norm_name(r["name"]))
        verified = _norm_name(r["name"]) in wc or bool(tr and tr[0])
        if wheelchair_only and not verified:
            continue
        dist = None if r["km"] is None or pd.isna(r["km"]) else float(r["km"])
        kind_name = bool(food_kind in FOOD_KINDS and re.search(FOOD_KINDS[food_kind][1], str(r["name"])))
        floor = _txt(r.get("floor"))
        upstairs = bool(floor) and floor != "1층"
        rank = (-ds[0] * 2 + (dist or 0) / 2 - (3 if (verified and wheel_first) else (0.5 if verified else 0))
                - (2 if kind_name else 0)  # '흑돼지'를 찾으면 이름에 흑돼지가 들어간 가게를 앞으로
                + ((4 if upstairs else (1 if not floor else -0.5)) if avoid_upstairs else 0))  # 거동 불편: 1층 우선
        items.append({"name": r["name"], "food_type": r["food_type"], "km": None if dist is None else round(dist, 1),
                      "address": r["address"], "phone": "", "wheelchair_entry": verified,
                      "access_info": (f"관광공사 무장애 정보: {tr[1]}" if tr and tr[0]
                                      else ("휠체어 진입 확인(2021 무장애 조사)" if verified else "입구 정보 없음")),
                      "baby_chair": bool(tr and tr[2]),
                      "floor": floor,
                      "floor_note": ("1층" if floor == "1층" else (f"{floor} · 엘리베이터 확인 필요" if floor else "층 정보 없음")),
                      "why": ds[1], "open_status": "2025 상가 자료에 있음",
                      "lat": float(r["lat"]), "lon": float(r["lon"]), "_rank": rank})
    items.sort(key=lambda x: (x["_rank"], x["name"]))
    seen, out = set(), []
    for it in items:  # 같은 이름 체인점 중복 제거
        k = _norm_name(it["name"])
        if k in seen:
            continue
        seen.add(k)
        it.pop("_rank")
        out.append(it)
        if len(out) >= int(limit):
            break
    for it in out:  # 카카오로 전화번호·장소 링크 보강(상가 자료에는 전화번호가 없음)
        kp = kakao_place(it["name"], it["lat"], it["lon"])
        it["name"] = clean_name(it["name"])
        if kp:
            it["phone"], it["place_url"] = kp["phone"], kp["place_url"]
            it["name"] = kp.get("name") or it["name"]  # 카카오 공식 이름(띄어쓰기 포함)
    asks = [q for k in (diet_needs or []) for q in DIET_NEEDS.get(k, {}).get("ask", [])]
    return {
        "food_kind": food_kind, "diet_needs": diet_needs or [],
        "diet_labels": [DIET_NEEDS[k]["label"] for k in (diet_needs or []) if k in DIET_NEEDS],
        "around": center[2] if center else (city or "제주 전체"),
        "center": [center[0], center[1]] if center else None,
        "items": out, "unverified": [],
        "with_wheelchair_badge": sum(1 for i in out if i["wheelchair_entry"]),
        "call_questions": asks,
        "note": "메뉴는 업종과 가게 이름으로 추정했어요. 건강 상태에 맞는지는 가게에 전화로 꼭 확인해 주세요."
                " 휠체어 배지는 2021년 무장애 조사와 한국관광공사 무장애 정보, 전화번호는 카카오 장소 정보예요.",
    }


CALL_QUESTIONS = {
    "manual_wheelchair": ["몇 층인가요? 엘리베이터가 있나요?", "입구에 턱이나 계단이 있나요?", "휠체어가 들어갈 만큼 문이 넓은가요?", "장애인 화장실이 있나요?", "가까운 곳에 주차할 수 있나요?"],
    "electric_wheelchair": ["몇 층인가요? 엘리베이터가 있나요?", "입구에 턱이나 계단이 있나요?", "전동 휠체어가 들어갈 만큼 통로가 넓은가요?", "장애인 화장실이 있나요?"],
    "stroller": ["몇 층인가요? 유모차로 올라갈 엘리베이터가 있나요?", "유모차를 끌고 들어갈 수 있나요?", "기저귀 갈 곳이나 수유실이 있나요?", "아기 의자가 있나요?"],
    "pregnant": ["몇 층인가요? 엘리베이터가 있나요?", "등받이 있는 의자에 앉을 수 있나요(좌식만 있는지)?",
                 "화장실이 가까운가요?", "임산부 주차구역이 있나요?"],
    "senior": ["몇 층인가요? 엘리베이터가 있나요?", "입구에 계단이 많은가요?", "의자에 앉는 자리가 있나요(좌식만 있는지)?", "화장실이 가까운가요?"],
    "other": ["입구에 턱이나 계단이 있나요?", "화장실이 있나요?"],
}


def call_questions(user_type="other", diet_needs=None):
    """가기 전 전화로 물어볼 질문(이동 유형 + 식사 조건). 오래된 정보의 한계를 사용자가 직접 확인할 수 있게 돕는다."""
    qs = list(CALL_QUESTIONS.get(user_type, CALL_QUESTIONS["other"]))
    for k in diet_needs or []:
        qs += [q for q in DIET_NEEDS.get(k, {}).get("ask", []) if q not in qs]
    return qs


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
    from urllib.parse import quote
    return f"https://map.kakao.com/link/to/{quote(str(name), safe='')},{lat},{lon}"


# ---------- 하루 나들이 일정 ----------
def place_stop(place, user_type="other"):
    """일정에 넣을 '장소' 한 곳(코스·시설 공통)."""
    d = get_place_detail(place, user_type)
    if "error" in d:
        return None
    pt = d["all_points"][0] if d.get("all_points") else None
    pl = load()["places"]
    r = pl[pl["place"] == d["place"]].iloc[0]
    return {"kind": "place", "name": d["place"], "where": d["where"], "lat": float(r["start_lat"]),
            "lon": float(r["start_lon"]), "verdict": d["verdict"], "verdict_reason": d["verdict_reason"],
            "checks": d["checks"], "key_points": d.get("key_points", [])[:6], "toilets_near": d.get("toilets_near", []),
            "minutes": d.get("minutes"), "tel": d.get("tel", ""), "source": d["source"],
            "phone": _txt(r.get("phone")), "parking": parking_point(d["place"]),
            "rain_alt": rain_alternative(d["place"], user_type),
            "entry_hint": pt["text"] if pt and d.get("data_kind") == "시설(관광공사)" else ""}


MOBILITY_TYPES = ("manual_wheelchair", "electric_wheelchair", "stroller", "senior", "pregnant")


def food_stop(item):
    """일정에 넣을 '식당·카페' 한 곳(search_food 결과 항목)."""
    return {"kind": "food", "name": item["name"], "where": item.get("address", ""), "lat": item["lat"], "lon": item["lon"],
            "food_type": item.get("food_type", ""), "why": item.get("why", []), "phone": item.get("phone", ""),
            "wheelchair_entry": item.get("wheelchair_entry", False), "access_info": item.get("access_info", ""),
            "baby_chair": item.get("baby_chair", False), "place_url": item.get("place_url", ""),
            "floor_note": item.get("floor_note", "")}


def plan_outing(user_type="other", area=None, theme=None, diet_needs=None, with_cafe=False, need_toilet=False,
                origin_lat=None, origin_lon=None, exclude=None):
    """반나절 나들이 일정: 장소 1곳 → 근처 식당 1곳(식사 조건 반영) → (원하면) 카페 1곳.
    사용자가 '일정·코스·반나절·하루'를 원할 때만 쓴다."""
    rec = recommend_places(user_type=user_type, area=area, theme=theme, need_toilet=need_toilet, limit=3,
                           origin_lat=origin_lat, origin_lon=origin_lon, exclude=exclude)
    if not rec["results"]:
        return {"stops": [], "note": "조건에 맞는 장소를 찾지 못했어요."}
    wheel = user_type in ("manual_wheelchair", "electric_wheelchair")
    chosen, food = None, None
    for cand in rec["results"]:  # 후보 중 근처(2km)에 식사할 곳이 있는 장소를 고른다
        f = search_food(place=cand["place"], diet_needs=diet_needs, prefer_wheelchair=wheel, limit=1, radius_km=2,
                        avoid_upstairs=user_type in MOBILITY_TYPES)
        if f["items"]:
            chosen, food = cand["place"], f
            break
    if chosen is None:  # 모두 외진 곳이면 1순위 장소에서 반경을 넓혀 찾는다
        chosen = rec["results"][0]["place"]
        food = search_food(place=chosen, diet_needs=diet_needs, prefer_wheelchair=wheel, limit=1, radius_km=8,
                           avoid_upstairs=user_type in MOBILITY_TYPES)
    first = place_stop(chosen, user_type)
    stops = [first]
    if food["items"]:
        stops.append(food_stop(food["items"][0]))
    if with_cafe:
        cafe = search_food(food_kind="카페", place=stops[-1]["name"], prefer_wheelchair=wheel, limit=1,
                           avoid_upstairs=user_type in MOBILITY_TYPES)
        if cafe["items"]:
            stops.append(food_stop(cafe["items"][0]))
    return {"user_type": USER_TYPES.get(user_type, "기타"), "stops": stops, "legs": itinerary_legs(stops),
            "note": "들르는 순서와 거리는 직선거리 기준 제안이에요. 실제 이동 시간은 길안내로 확인해 주세요."}


def itinerary_legs(stops):
    """들르는 곳 사이의 직선거리와 카카오맵 길안내 링크."""
    legs = []
    for a, b in zip(stops, stops[1:]):
        legs.append({"from": a["name"], "to": b["name"], "km": round(km(a["lat"], a["lon"], b["lat"], b["lon"]), 1),
                     "link": kakao_route_link(b["name"], b["lat"], b["lon"])})
    return legs


def itinerary_html(stops, user_type="other", diet_needs=None, when="오늘"):
    """일정표(한 장짜리 HTML). 브라우저로 열어 인쇄하거나 PDF로 저장한다."""
    import datetime as dt
    from html import escape as e
    if not stops:
        return ""
    wx = get_weather(place=stops[0]["name"] if stops[0]["kind"] == "place" else None,
                     area=None if stops[0]["kind"] == "place" else "제주시", when=when)
    help_ = find_nearby_help(stops[0]["name"]) if stops[0]["kind"] == "place" else {"help": {}}
    legs = itinerary_legs(stops)
    parts = []
    for i, s in enumerate(stops, 1):
        if i > 1:
            lg = legs[i - 2]
            parts.append(f'<div class="leg">↓ 약 {lg["km"]}km (직선) · <a href="{e(lg["link"])}">카카오맵 길안내</a></div>')
        if s["kind"] == "place":
            checks = "".join(f'<tr><td>{e(c["item"])}</td><td>{e(c["status"])}</td>'
                             f'<td>{"확인됨" if c["known"] else "확인 안 됨"}</td></tr>' for c in s["checks"])
            kp = "".join(f'<li>출발 후 약 {k["at_m"]}m · {e(k["label"])} ({e(", ".join(k["flags"]))})</li>'
                         for k in s["key_points"])
            toil = "".join(f'<li>{e(t["name"])} ({int(t["km"] * 1000)}m){" · 기저귀 교환대" if t["diaper"] else ""}</li>'
                           for t in s["toilets_near"])
            parts.append(f'''<section><h2>{i}. {e(s["name"])} <span class="v">{e(s["verdict"])}</span></h2>
<p class="sub">{e(s["where"])} · {e(s["verdict_reason"])}</p>
<table><tr><th>항목</th><th>내용</th><th>상태</th></tr>{checks}</table>
{f"<h3>코스에서 확인할 곳</h3><ul>{kp}</ul>" if kp else ""}
{f"<h3>가까운 장애인 화장실</h3><ul>{toil}</ul>" if toil else ""}
{f'<p>장애인 주차: <a href="{e(s["parking"]["link"])}">{e(s["parking"]["label"])} 위치로 길안내</a></p>' if s.get("parking") else ""}
{f'<p>비 오면 대신: <b>{e(s["rain_alt"]["name"])}</b> ({s["rain_alt"]["km"]}km, {e(s["rain_alt"]["verdict"])})</p>' if s.get("rain_alt") else ""}
<p class="src">자료: {e(s["source"])}</p></section>''')
        else:
            why = " · ".join(w.split(": ", 1)[-1] for w in s["why"])
            badge = "휠체어 진입 확인" if s["wheelchair_entry"] else "입구 정보 없음(전화 확인)"
            parts.append(f'''<section><h2>{i}. {e(s["name"])} <span class="v">{e(badge)}</span></h2>
<p class="sub">{e(s["food_type"])} · {e(s.get("floor_note", ""))} · {e(s["where"])}</p>
{f"<p>추천 이유(추정): {e(why)}</p>" if why else ""}
<p>전화: {e(s["phone"]) or "번호 정보 없음"}{" · 아기 의자 있음" if s["baby_chair"] else ""}</p></section>''')
    calls = call_questions(user_type, diet_needs)
    help_li = "".join(f'<li>{e(k)}: {e(v[0]["name"])} ({v[0]["km"]}km){" · " + e(v[0]["phone"]) if v[0].get("phone") else ""}</li>'
                      for k, v in help_.get("help", {}).items() if v and k in ("응급실", "약국", "병·의원"))
    wx_line = (f'{e(wx["date"])} 날씨: 비 올 확률 {wx["rain_chance"]}% · 바람 {wx["wind_ms"]:.0f}m/s · {e(wx["temp"])}'
               + ("".join(f"<br>⚠ {e(t)}" for t in wx["tips"]))) if wx.get("available") else "날씨는 출발 전 확인해 주세요."
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>제주 같이나들이 일정표</title>
<style>
@page {{ size: A4; margin: 14mm; }}
body {{ font-family: "Malgun Gothic", "Noto Sans KR", sans-serif; color:#16202A; font-size:12pt; line-height:1.55; }}
h1 {{ font-size:20pt; margin:0 0 4pt; }} h2 {{ font-size:14pt; margin:10pt 0 2pt; }} h3 {{ font-size:11.5pt; margin:8pt 0 2pt; }}
.sub {{ color:#4a5563; margin:0 0 6pt; }} .v {{ font-size:10pt; background:#E3F1EC; color:#0B6B55; padding:1pt 6pt; border-radius:8pt; }}
section {{ border:1.5pt solid #0B6B55; border-radius:8pt; padding:8pt 12pt; margin:6pt 0; break-inside:avoid; }}
table {{ border-collapse:collapse; width:100%; font-size:10.5pt; }} th, td {{ border-bottom:1pt solid #D3DED9; padding:3pt 5pt; text-align:left; }}
.leg {{ text-align:center; color:#0B6B55; font-weight:700; margin:4pt 0; }}
.box {{ background:#F1F6F4; border-radius:8pt; padding:8pt 12pt; margin:8pt 0; break-inside:avoid; }}
.src, .foot {{ color:#5d6676; font-size:9.5pt; }} a {{ color:#0B6B55; }}
</style></head><body>
<h1>제주 같이나들이 일정표</h1>
<p class="sub">{dt.date.today().isoformat()} 작성 · 함께 가는 분: {e(USER_TYPES.get(user_type, "기타"))}</p>
<div class="box">{wx_line}</div>
{"".join(parts)}
<div class="box"><h3>급할 때</h3><ul>{help_li}<li>응급 상황에는 119</li></ul></div>
<div class="box"><h3>가기 전 전화로 확인할 것</h3><ul>{"".join(f"<li>{e(q)}</li>" for q in calls)}</ul></div>
<p class="foot">거리는 직선거리예요. 무장애 정보는 제주특별자치도(2020~2021 조사)·한국관광공사, 식당은 2025 상가 자료·카카오 장소 정보, 날씨는 Open-Meteo 예보예요. 현장과 다를 수 있으니 방문 전 확인해 주세요.</p>
</body></html>'''


# ---------- 장애인 주차구역 좌표 (Last 50m) ----------
@lru_cache(maxsize=1)
def _parking_points():
    """제주도 조사 지점 중 '장애인 주차'가 확인된 첫 지점. 길안내를 장소 중심이 아니라 이 좌표로 찍는다."""
    p = load()["points"]
    p = p[p["accessible_parking"] == "yes"].copy()
    p["order"] = pd.to_numeric(p["order"], errors="coerce")
    p = p.sort_values(["place", "order"]).drop_duplicates("place")
    return {r["place"]: {"lat": float(r["lat"]), "lon": float(r["lon"]), "label": str(r["label"]),
                         "link": kakao_route_link(f"{r['place']} 장애인 주차", float(r["lat"]), float(r["lon"]))}
            for _, r in p.iterrows()}


def parking_point(place):
    return _parking_points().get(place)


# ---------- 비 올 때 대안 (Plan B) ----------
def rain_alternative(place, user_type="other", exclude=None):
    """바깥 장소라면 가까운 실내 장소 하나를 '비 오면 대신 갈 곳'으로 준다. 이미 실내면 None."""
    pl = load()["places"]
    row = pl[pl["place"] == place]
    if row.empty or "실내" in str(row.iloc[0]["themes"]):
        return None
    r = row.iloc[0]
    rec = recommend_places(user_type=user_type, theme="실내", limit=1, origin_lat=float(r["start_lat"]),
                           origin_lon=float(r["start_lon"]), exclude=[place] + list(exclude or []), with_evidence=False)
    if not rec["results"]:
        return None
    x = rec["results"][0]
    return {"name": x["place"], "km": x["distance_km"], "verdict": x["verdict"], "lat": x["lat"], "lon": x["lon"]}
