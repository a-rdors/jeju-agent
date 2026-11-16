"""외부 무료 API로 데이터를 보강한다(한 번 받아 저장해 두고 실행 중에는 저장본을 쓴다).

1) 한국관광공사 무장애 여행 정보(KorWithService2): 제주(lDongRegnCd=50) 목록 + 장소별 무장애 상세
   -> data/raw/tour/list.json, data/raw/tour/detail/{contentid}.json, data/processed/tour_places.csv
2) 공중화장실(제주): 주소를 카카오 주소 검색으로 좌표 변환
   -> data/raw/toilet/geocode_cache.json, data/processed/toilets.csv

필요한 키(.env): TOUR_API_KEY(공공데이터포털), KAKAO_REST_KEY(카카오 REST API)
실행: python scripts/06_fetch_external.py
여러 번 실행해도 이미 받은 것은 다시 받지 않는다(하루 호출 한도 보호).
"""
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
ENV = dotenv_values(ROOT / ".env")
RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"
TOUR = "https://apis.data.go.kr/B551011/KorWithService2/"
TYPE_NAMES = {"12": "관광지", "14": "문화시설", "15": "축제·공연", "25": "여행코스", "28": "레포츠",
              "32": "숙박", "38": "쇼핑", "39": "음식점"}
# 무장애 상세 항목(관광공사 detailWithTour2) -> 한글 이름
BF_FIELDS = {
    "parking": "주차", "route": "출입 경로", "publictransport": "대중교통", "ticketoffice": "매표소",
    "promotion": "홍보물", "wheelchair": "휠체어", "exit": "출입문", "elevator": "엘리베이터",
    "restroom": "화장실", "auditorium": "관람석", "room": "객실", "handicapetc": "지체장애 기타",
    "braileblock": "점자블록", "helpdog": "보조견", "guidehuman": "안내 요원", "audioguide": "오디오 가이드",
    "bigprint": "큰 활자", "brailepromotion": "점자 홍보물", "guidesystem": "유도 안내", "blindhandicapetc": "시각장애 기타",
    "signguide": "수어 안내", "videoguide": "자막 안내", "hearingroom": "청각 객실", "hearinghandicapetc": "청각장애 기타",
    "stroller": "유모차", "lactationroom": "수유실", "babysparechair": "유아용 의자", "infantsfamilyetc": "영유아 기타",
}


def tour_call(op, **params):
    p = {"serviceKey": ENV["TOUR_API_KEY"], "MobileOS": "ETC", "MobileApp": "jeju-gachi", "_type": "json", **params}
    with urllib.request.urlopen(TOUR + op + "?" + urllib.parse.urlencode(p), timeout=30) as r:
        body = json.loads(r.read().decode("utf-8"))["response"]["body"]
    items = body.get("items") or {}
    items = items.get("item") if isinstance(items, dict) else []
    items = [items] if isinstance(items, dict) else (items or [])
    return int(body.get("totalCount") or 0), items


def fetch_tour():
    (RAW / "tour" / "detail").mkdir(parents=True, exist_ok=True)
    list_path = RAW / "tour" / "list.json"
    if list_path.exists():
        items = json.loads(list_path.read_text(encoding="utf-8"))
    else:
        items, page = [], 1
        while True:
            total, got = tour_call("areaBasedList2", lDongRegnCd=50, numOfRows=100, pageNo=page)
            items += got
            if len(items) >= total or not got:
                break
            page += 1
            time.sleep(0.2)
        list_path.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    print("관광공사 제주 목록", len(items))
    new = 0
    for it in items:
        path = RAW / "tour" / "detail" / f"{it['contentid']}.json"
        if path.exists():
            continue
        try:
            _, d = tour_call("detailWithTour2", contentId=it["contentid"])
        except Exception as e:  # 한도 초과 등: 받은 데까지만 저장하고 다음 실행 때 이어 받는다
            print("상세 받기 중단:", type(e).__name__, "· 다음 실행 때 이어서 받음")
            break
        path.write_text(json.dumps(d[0] if d else {}, ensure_ascii=False), encoding="utf-8")
        new += 1
        time.sleep(0.15)
    print("상세 새로 받음", new)

    # 기본정보(전화·홈페이지·소개): 관광지·문화시설·음식점만
    (RAW / "tour" / "common").mkdir(parents=True, exist_ok=True)
    got = 0
    for it in items:
        if str(it.get("contenttypeid")) not in ("12", "14", "39"):
            continue
        path = RAW / "tour" / "common" / f"{it['contentid']}.json"
        if path.exists():
            continue
        try:
            _, d = tour_call("detailCommon2", contentId=it["contentid"])
        except Exception as e:
            print("기본정보 받기 중단:", type(e).__name__, "· 다음 실행 때 이어서 받음")
            break
        path.write_text(json.dumps(d[0] if d else {}, ensure_ascii=False), encoding="utf-8")
        got += 1
        time.sleep(0.15)
    print("기본정보 새로 받음", got)

    rows = []
    for it in items:
        path = RAW / "tour" / "detail" / f"{it['contentid']}.json"
        d = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        cpath = RAW / "tour" / "common" / f"{it['contentid']}.json"
        c = json.loads(cpath.read_text(encoding="utf-8")) if cpath.exists() else {}
        row = {"contentid": it["contentid"], "type": TYPE_NAMES.get(str(it.get("contenttypeid")), "기타"),
               "title": it.get("title", ""), "address": it.get("addr1", ""),
               "lat": float(it["mapy"]) if it.get("mapy") else None, "lon": float(it["mapx"]) if it.get("mapx") else None,
               "tel": c.get("tel") or it.get("tel", ""), "tel_name": c.get("telname", ""),
               "homepage": re.sub(r"<[^>]+>", " ", c.get("homepage", "") or "").strip(),
               "overview": re.sub(r"<[^>]+>|\s+", " ", c.get("overview", "") or "").strip()[:400],
               "image": it.get("firstimage", ""), "detail_loaded": bool(d)}
        for k, name in BF_FIELDS.items():
            row[name] = re.sub(r"\s+", " ", str(d.get(k) or "")).strip()
        rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(PROC / "tour_places.csv", index=False, encoding="utf-8-sig")
    print("tour_places.csv", len(df), df["type"].value_counts().to_dict())


def kakao_geocode(address, cache):
    if address in cache:
        return cache[address]
    url = "https://dapi.kakao.com/v2/local/search/address.json?" + urllib.parse.urlencode({"query": address})
    req = urllib.request.Request(url, headers={"Authorization": "KakaoAK " + ENV["KAKAO_REST_KEY"]})
    with urllib.request.urlopen(req, timeout=20) as r:
        docs = json.loads(r.read().decode("utf-8"))["documents"]
    cache[address] = (float(docs[0]["y"]), float(docs[0]["x"])) if docs else None
    time.sleep(0.05)
    return cache[address]


def fetch_toilets():
    src = next((RAW / "toilet").glob("공중화장실*.csv"))
    t = pd.read_csv(src, encoding="cp949")
    cache_path = RAW / "toilet" / "geocode_cache.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    lat, lon, how = [], [], []
    for road, jibun in zip(t["소재지도로명주소"], t["소재지지번주소"]):
        got, used = None, ""
        for a in (road, jibun):
            if isinstance(a, str) and a.strip():
                q = re.sub(r",.*$|\(.*?\)", "", a).strip()  # '도남로12길 8, 도남청소년문화의집' -> 주소 부분만
                got = kakao_geocode(q, cache)
                if got:
                    used = "도로명" if a is road else "지번"
                    break
        lat.append(got[0] if got else None)
        lon.append(got[1] if got else None)
        how.append(used)
    cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    n = lambda c: pd.to_numeric(t[c], errors="coerce").fillna(0)
    out = pd.DataFrame({
        "name": t["화장실명"], "kind": t["구분명"], "address": t["소재지도로명주소"].fillna(t["소재지지번주소"]),
        "lat": lat, "lon": lon, "geocoded_by": how,
        "accessible": (n("남성용-장애인용대변기수") + n("여성용-장애인용대변기수")) > 0,
        "accessible_count": (n("남성용-장애인용대변기수") + n("여성용-장애인용대변기수")).astype(int),
        "kids": (n("남성용-어린이용대변기수") + n("여성용-어린이용대변기수") + n("남성용-어린이용소변기수")) > 0,
        "diaper": t["기저귀교환대유무"].eq("Y"), "diaper_where": t["기저귀교환대장소"].fillna(""),
        "bell": t["비상벨설치여부"].eq("Y"), "open": t["개방시간"].fillna(""), "open_detail": t["개방시간상세"].fillna(""),
        "phone": t["전화번호"].fillna(""), "base_date": t["데이터기준일자"].fillna(""),
    })
    out.to_csv(PROC / "toilets.csv", index=False, encoding="utf-8-sig")
    print("toilets.csv", len(out), "좌표 있음", out["lat"].notna().sum(), "장애인용", int(out["accessible"].sum()),
          "기저귀", int(out["diaper"].sum()))


def _norm(x):
    return re.sub(r"\(.*?\)|\s|-|제주특별자치도|제주", "", str(x))


def fetch_place_contacts():
    """나들이 장소(places_app.csv)의 전화번호·카카오맵 링크를 카카오 키워드 검색으로 찾는다.
    주차장·버스정류장처럼 엉뚱한 곳이 잡히지 않게 분류를 거르고, 이름이 겹칠 때만 채택한다.
    03_build_support.py를 먼저 실행해 places_app.csv가 있어야 한다."""
    places = pd.read_csv(PROC / "places_app.csv")
    cache_path = RAW / "kakao_place_cache.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    rows = []
    for _, r in places.iterrows():
        name = str(r["place"])
        if name not in cache:
            q = re.sub(r"\(.*?\)", "", name).split("-")[0].strip()
            url = "https://dapi.kakao.com/v2/local/search/keyword.json?" + urllib.parse.urlencode(
                {"query": q, "x": r["start_lon"], "y": r["start_lat"], "radius": 1500, "sort": "accuracy"})
            req = urllib.request.Request(url, headers={"Authorization": "KakaoAK " + ENV["KAKAO_REST_KEY"]})
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    docs = json.loads(resp.read().decode("utf-8"))["documents"]
            except Exception:
                docs = None
            cache[name] = docs
            time.sleep(0.05)
        docs = cache.get(name) or []
        key = _norm(name)
        hit = None
        for d in docs:
            if re.search(r"주차장|정류장|정류소|버스|편의점|화장실", d.get("category_name", "") + d["place_name"]):
                continue
            pk = _norm(d["place_name"])
            if pk and (pk in key or key in pk or (len(key) >= 4 and key[:4] in pk)):
                hit = d
                break
        rows.append({"place": name, "phone": (hit or {}).get("phone", ""), "place_url": (hit or {}).get("place_url", ""),
                     "kakao_name": (hit or {}).get("place_name", "")})
    cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    out = pd.DataFrame(rows)
    out.to_csv(PROC / "place_contacts.csv", index=False, encoding="utf-8-sig")
    print("place_contacts.csv", len(out), "전화 있음", (out["phone"].fillna("") != "").sum(),
          "카카오맵 링크", (out["place_url"].fillna("") != "").sum())


if __name__ == "__main__":
    import sys
    if "contacts" in sys.argv:  # 03 실행 후: python scripts/06_fetch_external.py contacts
        fetch_place_contacts()
    else:
        fetch_toilets()
        fetch_tour()
