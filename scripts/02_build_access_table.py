"""무장애 여행 위치 설명 문장을 비교 가능한 접근성 표로 바꾼다.

입력: data/raw/mujangae/{location,nearby,general}/*.csv  (01_download_mujangae.py 결과)
      data/제주특별자치도 상가(상권) 정보.csv            (장소의 시·동 이름을 좌표로 찾기 위해 사용)
출력: data/processed/points.csv     지점별 추출 결과 (원문 포함)
      data/processed/places.csv     장소별 요약
      data/processed/nearby.csv     장소별 주변시설
      data/processed/companion.csv  장소·이동유형별 추천/보호자 동반 권장

규칙 기반 추출이라 같은 입력이면 항상 같은 결과가 나온다(재현성).
실행: python scripts/02_build_access_table.py
"""
import csv
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "mujangae"
OUT = ROOT / "data" / "processed"
SANGGA = ROOT / "data" / "제주특별자치도 상가(상권) 정보.csv"

# 「장애인·노인·임산부 등의 편의증진 보장에 관한 법률 시행규칙」 별표1 접근로 기울기
# 1/18 이하, 지형상 곤란하면 1/12까지 완화 -> 각도로 환산
SLOPE_STD = math.degrees(math.atan(1 / 18))    # 약 3.18도
SLOPE_RELAX = math.degrees(math.atan(1 / 12))  # 약 4.76도

BOILER = re.compile(r"접근성정보\(\*계단\.\s*길 상태\.\s*경사\)\s*있음")
# 각도 기호(°, º, ˚)는 뒤에 조사가 붙어도 각도. '도'는 '도로'와 헷갈리지 않게 뒤에 한글이 없을 때만
DEG = re.compile(r"(\d+(?:\.\d+)?)\s*(?:도|º|°|˚)?\s*(?:[~\-]\s*(\d+(?:\.\d+)?))?\s*(?:[º°˚]|도(?![가-힣]))")
CM = re.compile(r"(\d+(?:\.\d+)?)\s*(?:cm|CM|㎝|센티)")
STAIR_N = [re.compile(r"계단\s*:?\s*(\d+)\s*(?:개|칸)"), re.compile(r"(\d+)\s*(?:개|칸)의?\s*계단")]
BLOCKED = re.compile(r"(?:접근|진입|출입|이동|이용|접금)\s*(?:이\s*|은\s*)?(?:불가|어려|힘듦|힘들)|불가능|이용\s*불가|이용불가|진입불가|출입불가")
HELP = re.compile(r"도움|동행|이동\s*지원")
CAUTION = re.compile(r"주의|위험|미끄")
SURFACES = ["자갈", "잔디", "흙", "모래", "판석", "비포장", "울퉁불퉁", "데크", "테크", "야자매트", "야자수 매트", "보도블럭", "돌길", "송이"]
NEG_AFTER = re.compile(r"^\s*(?:구역|칸|장|공간)?\s*[:：]?\s*(?:x|X|없|확인\s*X|확인x)")


def read_csv(path):
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "cp949"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    import io
    return [{(k or "").strip(): (v or "").strip() for k, v in r.items()} for r in csv.DictReader(io.StringIO(text))]


EXTRA_BOILER = re.compile(r"특이사항\s*없음|접근성\s*정보\s*있음\s*\(계단 혹은 경사 있음\.\s*길 상태 안 좋음\)")


def read_extra(path):
    """2020년 조사 관광지 파일(형식 2가지)을 위치정보 형식으로 맞춘다.
    형식 A: 위도,경도,장소명칭,장소상세정보,무장애관광정보,추천코스여부,데이터품질점검결과,데이터기준일자
    형식 B: ID,lat,lon,title,Description,Image,Point,info,A,B,etc  (A·B는 코스 표시. etc는 범례라 쓰지 않음)"""
    rows = read_csv(path)
    out = []
    for i, r in enumerate(rows, 1):
        if "위도" in r:
            detail = EXTRA_BOILER.sub("", r.get("장소상세정보", "")).strip()
            access = EXTRA_BOILER.sub("", r.get("무장애관광정보", "")).strip()
            out.append({"순서": str(i), "위도": r["위도"], "경도": r["경도"], "구분": r.get("장소명칭", ""),
                        "설명": detail, "상세정보": access, "추천코스여부": r.get("추천코스여부", "Y") or "Y",
                        "데이터기준일자": r.get("데이터기준일자", "2020-12-22")})
        else:
            title = r.get("title") or r.get("Title") or ""
            on = "Y" if (r.get("A") or r.get("B")) else "N"
            out.append({"순서": r.get("ID", str(i)), "위도": r.get("lat", ""), "경도": r.get("lon", ""), "구분": title,
                        "설명": " ".join((r.get("Description") or "").split()), "상세정보": r.get("info", ""),
                        "추천코스여부": on, "데이터기준일자": "2020-12-14"})
    return [o for o in out if o["위도"] and o["경도"]]


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def has_positive(text, pattern):
    """'장애인 주차구역 1대'는 있음, '장애인 주차구역x'·'없음'은 없음으로 본다."""
    found, negated = False, False
    for m in re.finditer(pattern, text):
        if NEG_AFTER.match(text[m.end():m.end() + 8]):
            negated = True
        else:
            found = True
    return "yes" if found else ("no" if negated else "")


def extract(text):
    slopes = []
    for m in DEG.finditer(text):
        vals = [float(v) for v in m.groups() if v]
        slopes += [v for v in vals if v <= 45]
    steps, widths = [], []
    for m in CM.finditer(text):
        ctx = text[max(0, m.start() - 14):m.start()]
        v = float(m.group(1))
        after = text[m.end():m.end() + 5]
        if re.search(r"폭|넓이|통로", ctx):
            if v >= 30:  # 30cm 미만 '폭'은 통로가 아니라 바닥 틈·홈의 폭
                widths.append(v)
        elif (re.search(r"단차|턱|경계석", ctx) or re.search(r"단차|턱", after)) and not re.search(r"방파제|돌담|둑", ctx):
            steps.append(v)
    stair_n = [int(m.group(1)) for p in STAIR_N for m in p.finditer(text)]
    # '계단 | 10개'처럼 구분 칸에 계단, 설명 칸에 개수만 있는 경우
    if not stair_n and text.startswith("계단"):
        stair_n = [int(m.group(1)) for m in re.finditer(r"(\d+)\s*(?:개|칸)", text)]
    return {
        "slope_max_deg": max(slopes) if slopes else "",
        "step_max_cm": max(steps) if steps else "",
        "width_min_cm": min(widths) if widths else "",
        "stairs": "yes" if "계단" in text else "",
        "stairs_count": max(stair_n) if stair_n else "",
        "blocked": "yes" if BLOCKED.search(text) else "",
        "needs_help": "yes" if HELP.search(text) else "",
        "caution": "yes" if CAUTION.search(text) else "",
        "steep_word": "yes" if re.search(r"급경사|가파르|가파른|가팔", text) else "",
        "surface": "/".join(s for s in SURFACES if s in text.replace("벽돌", "벽_돌")),  # '벽돌길'은 돌길 아님
        "accessible_toilet": "no" if ("화장실" in text and re.search(r"장애인\s*[xX]", text)) else has_positive(text, r"장애인\s*(?:남녀\s*구분\s*)?화장실|장애인\s*칸|장애인화장실\s*O|장애남녀"),
        "accessible_parking": has_positive(text, r"장애인\s*주차(?:구역|장|공간)?"),
    }


def slope_grade(deg):
    if deg == "":
        return "기록 없음"
    if deg <= SLOPE_STD:
        return "기준 이내"
    if deg <= SLOPE_RELAX:
        return "완화 기준 이내"
    return "기준 초과"


def load_region_index():
    """상가 정보 좌표로 장소의 시군구·행정동을 찾는 간단한 격자 색인."""
    grid = {}
    head = SANGGA.read_bytes()[:200]
    enc = "utf-8-sig"
    try:
        head.decode("utf-8")
    except UnicodeDecodeError:
        enc = "cp949"
    with open(SANGGA, encoding=enc, errors="replace", newline="") as f:
        for r in csv.DictReader(f):
            try:
                lon, lat = float(r["경도"]), float(r["위도"])
            except (ValueError, KeyError):
                continue
            grid.setdefault((round(lat, 2), round(lon, 2)), []).append((lat, lon, r["시군구명"], r["행정동명"]))
    return grid


def nearest_region(grid, lat, lon):
    best = None
    steps = (-0.03, -0.02, -0.01, 0, 0.01, 0.02, 0.03)
    for dy in steps:
        for dx in steps:
            for p in grid.get((round(lat + dy, 2), round(lon + dx, 2)), []):
                d = (p[0] - lat) ** 2 + (p[1] - lon) ** 2
                if best is None or d < best[0]:
                    best = (d, p[2], p[3])
    return (best[1], best[2]) if best else ("", "")


def main():
    points, places = [], []
    grid = load_region_index()

    sources = [(p, p.stem, read_csv, "2021 마을·해안길 조사") for p in sorted((RAW / "location").glob("*.csv"))]
    extra_dir = ROOT / "data" / "raw" / "mujangae_extra"
    sources += [(p, p.stem.replace("제주특별자치도_무장애여행정보_", ""), read_extra, "2020 관광지 조사")
                for p in sorted(extra_dir.glob("*.csv"))]
    for path, place, reader, survey in sources:
        rows = reader(path)
        place_points = []
        for r in rows:
            label = r.get("구분", "")
            if label.startswith("삭제"):
                continue
            raw = " | ".join(x for x in (label, r.get("설명", ""), r.get("상세정보", "")) if x)
            text = BOILER.sub("", raw).strip(" |.")
            on_route = r.get("추천코스여부", "") == "Y" and "비장애인" not in text
            p = {"place": place, "order": r.get("순서", ""), "lat": r.get("위도", ""), "lon": r.get("경도", ""),
                 "label": label, "text": text, "on_route": "Y" if on_route else "N",
                 "base_date": r.get("데이터기준일자", "")}
            p.update(extract(text))
            # 장애인 화장실 표시 칸(상세정보)이 따로 있는 경우 반영
            if "장애인화장실" in r.get("상세정보", "") and p["accessible_toilet"] != "no":
                p["accessible_toilet"] = "yes"
            place_points.append(p)
        points += place_points

        route = [p for p in place_points if p["on_route"] == "Y"]
        side = [p for p in place_points if p["on_route"] == "N"]
        slopes = [p["slope_max_deg"] for p in route if p["slope_max_deg"] != ""]
        steps = [p["step_max_cm"] for p in route if p["step_max_cm"] != ""]
        max_slope = max(slopes) if slopes else ""
        lat, lon = float(place_points[0]["lat"]), float(place_points[0]["lon"])
        sigungu, dong = nearest_region(grid, lat, lon)
        places.append({
            "place": place, "sigungu": sigungu, "dong": dong,
            "start_lat": lat, "start_lon": lon, "points": len(place_points), "route_points": len(route),
            "route_slope_max_deg": max_slope, "slope_grade": slope_grade(max_slope),
            "route_slope_points": len(slopes),
            "route_over_relax_points": sum(1 for s in slopes if s > SLOPE_RELAX),
            "route_step_max_cm": max(steps) if steps else "",
            "route_stairs_points": sum(1 for p in route if p["stairs"]),
            "route_blocked_points": sum(1 for p in route if p["blocked"]),
            "route_help_points": sum(1 for p in route if p["needs_help"]),
            "route_steep_word_points": sum(1 for p in route if p["steep_word"]),
            "side_blocked_points": sum(1 for p in side if p["blocked"] or p["stairs"]),
            "rough_surface": "/".join(sorted({s for p in route for s in p["surface"].split("/") if s})),
            "accessible_toilet": "yes" if any(p["accessible_toilet"] == "yes" for p in place_points) else "",
            "accessible_parking": "yes" if any(p["accessible_parking"] == "yes" for p in place_points)
            else ("no" if any(p["accessible_parking"] == "no" for p in place_points) else ""),
            "base_date": place_points[0]["base_date"],
            "survey": survey,
        })

    # 법 기준으로는 대부분 '기준 초과'라 장소끼리 비교가 안 된다.
    # 그래서 경사 기록이 있는 장소들의 최대 경사를 3등분해 상대 난이도를 붙인다(임의 기준값 없음).
    recorded = sorted(p["route_slope_max_deg"] for p in places if p["route_slope_max_deg"] != "")
    cut1 = recorded[len(recorded) // 3]
    cut2 = recorded[(len(recorded) * 2) // 3]
    for p in places:
        s = p["route_slope_max_deg"]
        if s == "":
            p["slope_relative"] = "기록 없음"
        elif s < cut1:
            p["slope_relative"] = "완만한 편"
        elif s < cut2:
            p["slope_relative"] = "보통"
        else:
            p["slope_relative"] = "가파른 편"
    print(f"상대 난이도 경계: {cut1}도 미만 완만한 편, {cut2}도 미만 보통, 그 이상 가파른 편")

    nearby = []
    for path in sorted((RAW / "nearby").glob("*.csv")):
        for r in read_csv(path):
            if not r.get("명칭"):
                continue
            nearby.append({"place": path.stem, "category": r.get("구분", ""), "name": r.get("명칭", ""),
                           "distance_km": r.get("거리(km)", ""), "address": r.get("주소", ""),
                           "phone": r.get("전화번호", ""),
                           "wheelchair_entry": "yes" if r.get("휠체어 진입") == "●" else "unknown",
                           "accessible_toilet": "yes" if r.get("장애인 화장실") == "●" else "unknown",
                           "base_date": r.get("데이터기준일자", "")})

    companion = []
    for path in sorted((RAW / "general").glob("*.csv")):
        for r in read_csv(path):
            kind = " ".join(x for x in (r.get("구분", ""), r.get("유형", "")) if x)
            companion.append({"place": path.stem, "user_type": kind,
                              "recommended": "yes" if r.get("추천여부") == "●" else "no",
                              "companion_advised": "yes" if "동반" in r.get("비고", "") else ""})

    pf = ["place", "order", "lat", "lon", "label", "text", "on_route", "slope_max_deg", "step_max_cm",
          "width_min_cm", "stairs", "stairs_count", "blocked", "needs_help", "caution", "steep_word", "surface",
          "accessible_toilet", "accessible_parking", "base_date"]
    write_csv(OUT / "points.csv", points, pf)
    write_csv(OUT / "places.csv", places, list(places[0].keys()))
    write_csv(OUT / "nearby.csv", nearby, list(nearby[0].keys()))
    write_csv(OUT / "companion.csv", companion, list(companion[0].keys()))
    print(f"지점 {len(points)} · 장소 {len(places)} · 주변시설 {len(nearby)} · 유형별 {len(companion)}")


if __name__ == "__main__":
    main()
