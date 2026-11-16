"""Agent가 바로 쓸 보조 표를 만든다.

입력: data/processed/{places,points,nearby}.csv (02 결과)
      data/제주특별자치도 상가(상권) 정보.csv (2025-09, 좌표 있음)
      data/제주특별자치도음식점목록(통합).csv (2025-08, 영업상태)
      data/제주응급실보유병원정보.csv (2021-08)
출력: data/processed/areas.csv          동네 이름 -> 대표 좌표 ("애월", "협재" 등)
      data/processed/medical.csv        약국·병의원·응급실 좌표
      data/processed/nearby_checked.csv 2021 주변시설 + 2025 영업 확인 결과
      data/processed/places_app.csv     장소 요약 + 테마, 코스 길이, 쉼터·화장실 위치

실행: python scripts/03_build_support.py
"""
import math
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PROC = DATA / "processed"

THEMES = {
    "바다": r"해안|포구|방파제|해수욕장|해변|바당|항|등대|알작지|넙빌레|환해장성|요트|바다",
    "마을": r"마을|골목|거리|벽화|리사무소|식당",
    "자연·숲": r"숲|동백|목장|생태|공원|저수지|오름|봉|월대천|밭담|군락|퐁낭|산책|휴양림|올레|폭포|정원|수목원|곶자왈|습지|분화구|계곡|섬|식물원|녹차|감귤",
    "역사·문화": r"사|법정사|항일|당터|유적|환해장성|이중섭|연대|기념관|박물관",
    "실내": r"박물관|미술관|갤러리|두모악|뮤지엄|벙커|센터|기념관|공연장",
    "시장": r"시장|오일장",
}
REST = r"쉼터|정자|벤치|의자|그늘|쉼팡|휴게"


def read(path, **kw):
    for enc in ("utf-8-sig", "cp949"):
        try:
            return pd.read_csv(path, encoding=enc, **kw)
        except UnicodeDecodeError:
            continue
    raise ValueError(path)


def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def norm(name):
    name = re.sub(r"\(.*?\)|\s|주식회사|\(주\)|본점$|점$", "", str(name))
    return name.lower()


def build_areas(sangga):
    rows = []
    s = sangga.dropna(subset=["위도", "경도"])
    for col in ("행정동명", "법정동명"):
        for (sgg, name), g in s.groupby(["시군구명", col]):
            rows.append((name, sgg, g["위도"].mean(), g["경도"].mean(), len(g)))
    # 읍·면 지역은 '협재리', '함덕리'처럼 리 이름으로 말하는 경우가 많다
    ri = s["지번주소"].str.extract(r"([가-힣]+[읍면])\s+([가-힣0-9]+리)\b")
    s2 = s.assign(eup=ri[0], ri=ri[1]).dropna(subset=["ri"])
    for (sgg, ri_name), g in s2.groupby(["시군구명", "ri"]):
        rows.append((ri_name, sgg, g["위도"].mean(), g["경도"].mean(), len(g)))
    df = pd.DataFrame(rows, columns=["area", "sigungu", "lat", "lon", "n"])
    # '애월읍'->'애월', '협재리'->'협재', '중문동'->'중문' 같은 짧은 이름도 등록
    short = df.copy()
    short["area"] = short["area"].str.replace(r"(읍|면|동|리)$", "", regex=True).str.replace(r"\d", "", regex=True)
    df = pd.concat([df, short[short["area"].str.len() >= 2]])
    return df.sort_values("n", ascending=False).drop_duplicates("area").reset_index(drop=True)


def build_medical(sangga, areas):
    s = sangga.dropna(subset=["위도", "경도"])
    ph = s[s["상권업종소분류명"] == "약국"]
    cl = s[(s["상권업종대분류명"] == "보건의료") & (s["상권업종소분류명"] != "유사 의료업")]
    med = pd.concat([
        pd.DataFrame({"kind": "약국", "name": ph["상호명"], "detail": "", "address": ph["도로명주소"],
                      "phone": "", "lat": ph["위도"], "lon": ph["경도"], "source": "상가(상권) 정보 2025-09"}),
        pd.DataFrame({"kind": "병·의원", "name": cl["상호명"], "detail": cl["상권업종소분류명"], "address": cl["도로명주소"],
                      "phone": "", "lat": cl["위도"], "lon": cl["경도"], "source": "상가(상권) 정보 2025-09"}),
    ])
    er = read(DATA / "제주응급실보유병원정보.csv")
    hosp = s[s["상권업종소분류명"].isin(["종합병원", "일반병원"])]
    for _, r in er.iterrows():
        key = norm(r["병원명"]).replace("의료법인", "")
        hit = hosp[hosp["상호명"].map(norm).map(lambda x: x in key or key.endswith(x))]
        if len(hit):
            lat, lon, how = hit.iloc[0]["위도"], hit.iloc[0]["경도"], "상가 좌표"
        else:  # 주소의 (동) 이름으로 대략 위치
            dong = re.search(r"\(([가-힣0-9]+동)", str(r["주소"]))
            a = areas[areas["area"] == (dong.group(1) if dong else "")]
            lat, lon, how = (a.iloc[0]["lat"], a.iloc[0]["lon"], "동 중심 좌표(대략)") if len(a) else (None, None, "")
        med.loc[len(med)] = {"kind": "응급실", "name": r["병원명"], "detail": f"평일 {r['화~금 진료 시간']}",
                             "address": r["주소"], "phone": r["대표전화"], "lat": lat, "lon": lon,
                             "source": f"제주 응급실 보유 병원 정보 2021-08 · {how}"}
    return med.dropna(subset=["lat"]).reset_index(drop=True)


def build_open_check(nearby, sangga, rest):
    rest = rest.assign(key=rest["사업장명"].map(norm), addr=rest["소재지전체주소"].fillna("") + " " + rest["도로명전체주소"].fillna(""))
    s = sangga.assign(key=sangga["상호명"].map(norm), addr=sangga["지번주소"].fillna("") + " " + sangga["도로명주소"].fillna(""))
    open_rest = rest[rest["영업상태명"].str.contains("영업")]
    closed_rest = rest[rest["영업상태명"].str.contains("폐업")]
    by_key = {
        "s": s.groupby("key")["addr"].apply(list).to_dict(),
        "o": open_rest.groupby("key")["addr"].apply(list).to_dict(),
        "c": closed_rest.groupby("key")["addr"].apply(list).to_dict(),
    }

    def same_area(addr_list, address):
        towns = re.findall(r"([가-힣]+[읍면동])\b", str(address))
        return any(any(t in a for t in towns) for a in addr_list) if towns else bool(addr_list)

    status = []
    for _, r in nearby.iterrows():
        k = norm(r["name"])
        if r["category"] == "주변 관광지":
            status.append("해당 없음")
        elif same_area(by_key["s"].get(k, []), r["address"]) or same_area(by_key["o"].get(k, []), r["address"]):
            status.append("영업 확인")
        elif same_area(by_key["c"].get(k, []), r["address"]):
            status.append("폐업 기록")
        else:
            status.append("확인 안 됨")
    return nearby.assign(open_status=status)


def course_metrics(points, place):
    p = points[(points["place"] == place) & (points["on_route"] == "Y")].copy()
    p["order"] = pd.to_numeric(p["order"], errors="coerce")
    p = p.sort_values("order")
    dist, acc, prev = [], 0.0, None
    for _, r in p.iterrows():
        if prev is not None:
            acc += haversine_m(prev[0], prev[1], r["lat"], r["lon"])
        dist.append(acc)
        prev = (r["lat"], r["lon"])
    p["from_start_m"] = dist
    rest = p[p["text"].fillna("").str.contains(REST)]
    toilet = p[p["accessible_toilet"] == "yes"]
    return {
        "course_m": round(acc),
        "rest_points": len(rest),
        "rest_at_m": "/".join(str(int(round(x, -1))) for x in rest["from_start_m"]),
        "toilet_at_m": "/".join(str(int(round(x, -1))) for x in toilet["from_start_m"]),
    }


TOUR_SURVEY = "관광공사 무장애 여행 정보"
ENTRY_OK = r"턱이 없|턱 없|단차가 없|단차 없|경사로|휠체어 접근 가능|휠체어 진입 가능|평지|무단차"
ENTRY_BAD = r"불가|어려|계단만|턱이 있|단차 있"


def add_tour_places(app):
    """관광공사 무장애 여행 정보(관광지·문화시설)를 나들이 장소 표에 합친다.
    제주도 조사 70곳은 '코스 경사' 자료, 관광공사는 '시설 입구·화장실·대여' 자료라 칸을 나눠 둔다."""
    path = PROC / "tour_places.csv"
    for col in ("entry_access", "entry_ok", "wheelchair_rental", "stroller_rental", "nursing_room", "elevator",
                "tour_type", "tel", "overview", "image", "homepage"):
        app[col] = ""
    if not path.exists():
        return app
    t = pd.read_csv(path).fillna("")
    t = t[t["type"].isin(["관광지", "문화시설"]) & t["lat"].astype(str).ne("")]
    alias = lambda x: re.sub(r"제주|국립|도립|특별자치도", "", norm(x).replace("특별자치도립", "도립"))
    have = [alias(x) for x in app["place"]]
    areas = pd.read_csv(PROC / "areas.csv", encoding="utf-8-sig")
    dongs = areas[areas["area"].str.contains(r"[읍면동]$", regex=True)]
    rows = []
    for _, r in t.iterrows():
        key = alias(r["title"])
        if any(key == h or (len(key) >= 4 and len(h) >= 4 and (key in h or h in key)) for h in have):
            continue  # 제주도 조사 장소와 겹치면 기존 장소를 쓴다
        addr = str(r["address"])
        sgg = "서귀포시" if "서귀포시" in addr else ("제주시" if "제주시" in addr else "")
        dong = re.search(r"([가-힣0-9]+[읍면동])(?:\s|$)", addr.replace("제주특별자치도", "").replace(sgg, ""))
        if not dong:  # 주소에 동 이름이 없으면 가장 가까운 읍·면·동 중심으로 채운다
            dd = (dongs["lat"] - float(r["lat"])) ** 2 + (dongs["lon"] - float(r["lon"])) ** 2
            nearest = dongs.loc[dd.idxmin()]
            dong_name = nearest["area"]
        else:
            dong_name = dong.group(1)
        entry = str(r["출입 경로"]) or str(r["출입문"])
        ok = bool(re.search(ENTRY_OK, entry)) and not re.search(ENTRY_BAD, entry)
        themes = [k for k, pat in THEMES.items() if re.search(pat, r["title"])]
        if r["type"] == "문화시설" and "실내" not in themes:
            themes.append("실내")
        rows.append({
            "place": r["title"], "sigungu": sgg, "dong": dong_name,
            "start_lat": float(r["lat"]), "start_lon": float(r["lon"]), "points": 1, "route_points": 0,
            "route_slope_points": 0, "route_over_relax_points": 0, "route_stairs_points": 0, "route_blocked_points": 0,
            "route_help_points": 0, "route_steep_word_points": 0, "side_blocked_points": 0,
            "slope_grade": "기록 없음", "slope_relative": "기록 없음",
            "accessible_toilet": "yes" if re.search(r"장애인", str(r["화장실"])) and "없" not in str(r["화장실"]) else "",
            "accessible_parking": "yes" if re.search(r"장애인", str(r["주차"])) and "없" not in str(r["주차"]) else "",
            "base_date": "관광공사 API(수시 갱신)", "survey": TOUR_SURVEY, "course_m": 0, "rest_points": 0,
            "themes": "/".join(themes) or "기타",
            "entry_access": entry, "entry_ok": "yes" if ok else ("no" if entry else ""),
            "wheelchair_rental": str(r["휠체어"]), "stroller_rental": str(r["유모차"]),
            "nursing_room": str(r["수유실"]), "elevator": str(r["엘리베이터"]),
            "tour_type": r["type"], "tel": str(r["tel"]),
            "overview": str(r.get("overview", "")), "image": str(r.get("image", "")),
            "homepage": (re.search(r"https?://[^\s\"'>]+", str(r.get("homepage", ""))) or [""])[0],
        })
    return pd.concat([app, pd.DataFrame(rows)], ignore_index=True)


FLOOR = re.compile(r"(지하\s*\d+\s*층|\d+\s*층)")


def floor_of(addr):
    m = FLOOR.search(str(addr))
    return re.sub(r"\s", "", m.group(1)) if m else ""


def attach_floor(food, rest):
    """음식점 목록(인허가, 2025)의 주소에 적힌 층(예: '…, 2층')을 같은 이름·같은 읍면동 가게에 붙인다."""
    op = rest[rest["영업상태명"].str.contains("영업", na=False)]
    addr = op["도로명전체주소"].fillna("") + " " + op["소재지전체주소"].fillna("")
    idx = {}
    for name, a in zip(op["사업장명"], addr):
        fl = floor_of(a)
        if fl:
            idx.setdefault(norm(name), []).append((a, fl))
    out = []
    for key, dong, address in zip(food["key"], food["dong"], food["address"]):
        cands = idx.get(key, [])
        town = re.sub(r"(\d)", "", str(dong))[:2]
        hit = next((fl for a, fl in cands if town and town in a), None)
        if hit is None and len(cands) == 1:
            hit = cands[0][1]
        out.append(hit or "")
    return out


def main():
    sangga = read(DATA / "제주특별자치도 상가(상권) 정보.csv")
    rest = read(DATA / "제주특별자치도음식점목록(통합).csv", low_memory=False)
    places = pd.read_csv(PROC / "places.csv")
    points = pd.read_csv(PROC / "points.csv")
    nearby = pd.read_csv(PROC / "nearby.csv")

    areas = build_areas(sangga)
    areas.to_csv(PROC / "areas.csv", index=False, encoding="utf-8-sig")
    med = build_medical(sangga, areas)
    med.to_csv(PROC / "medical.csv", index=False, encoding="utf-8-sig")
    checked = build_open_check(nearby, sangga, rest)
    # 주변시설에 2025 상가 업종·좌표를 붙인다(이름 + 같은 읍면동으로 연결)
    food = sangga[sangga["상권업종대분류명"] == "음식"].dropna(subset=["위도", "경도"])
    food = pd.DataFrame({"name": food["상호명"], "food_type": food["상권업종소분류명"], "sigungu": food["시군구명"],
                         "dong": food["행정동명"], "address": food["도로명주소"].fillna(food["지번주소"]),
                         "lat": food["위도"], "lon": food["경도"]})
    food["key"] = food["name"].map(norm)
    food["floor"] = attach_floor(food, rest)
    food.drop(columns="key").to_csv(PROC / "food.csv", index=False, encoding="utf-8-sig")
    print("층 정보", food["floor"].replace("", None).notna().sum(), "/", len(food),
          food["floor"].value_counts().head(5).to_dict())
    first = food.drop_duplicates("key").set_index("key")
    checked["key"] = checked["name"].map(norm)
    checked = checked.join(first[["food_type", "lat", "lon"]], on="key").drop(columns="key")
    checked.to_csv(PROC / "nearby_checked.csv", index=False, encoding="utf-8-sig")

    extra = []
    for _, pl in places.iterrows():
        m = course_metrics(points, pl["place"])
        themes = [t for t, pat in THEMES.items() if re.search(pat, pl["place"])]
        m.update({"place": pl["place"], "themes": "/".join(themes) or "기타"})
        extra.append(m)
    app = places.merge(pd.DataFrame(extra), on="place")
    app = add_tour_places(app)
    app.to_csv(PROC / "places_app.csv", index=False, encoding="utf-8-sig")
    print("나들이 장소", len(app), app["survey"].value_counts().to_dict())

    print("동네", len(areas), "| 의료", med["kind"].value_counts().to_dict(),
          "| 영업확인", checked["open_status"].value_counts().to_dict())
    print("코스 길이(m) 중앙값", int(app["course_m"].median()), "| 테마", app["themes"].value_counts().to_dict())


if __name__ == "__main__":
    main()
