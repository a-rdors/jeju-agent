"""코스 선을 실제 걷는 길 모양에 맞춘다 → data/processed/route_paths.json

지도의 코스 선은 조사 지점을 순서대로 이은 것이라, 지점 사이가 멀면 바다나 건물을 가로지르는 직선이 된다.
OpenStreetMap 도보 길찾기(OSRM, routing.openstreetmap.de)로 지점 사이의 길 모양을 받아,
믿을 만한 구간만 길 모양으로 바꾸고 나머지는 직선으로 둔다(화면은 직선 구간을 점선으로 그린다).

  믿을 만한 구간: 두 지점이 모두 길에서 SNAP_M 안쪽이고, 길로 돈 거리가 직선의 DETOUR 배 + SLACK_M 이하.
  (방파제·숲길처럼 OSM 에 없는 길은 먼 도로로 붙으므로 직선으로 남긴다)

조사 지점·순서·판정은 바꾸지 않는다. 선 모양만 바꾼다. 장소마다 한 번씩만 부르고 1초씩 쉰다.
실행: python scripts/08_route_paths.py   (화면 실행에는 필요 없음. 결과 파일을 커밋해 둔다)
경로 모양 자료: © OpenStreetMap 기여자(ODbL)
"""
import json
import math
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import tools as T  # noqa: E402

OUT = ROOT / "data" / "processed" / "route_paths.json"
OSRM = "https://routing.openstreetmap.de/routed-foot/route/v1/driving/"
SNAP_M, DETOUR, SLACK_M = 25, 1.6, 40


def dist(a, b):
    dy = (a[0] - b[0]) * 110540
    dx = (a[1] - b[1]) * 111320 * math.cos(math.radians(a[0]))
    return math.hypot(dx, dy)


def despike(pts):
    """web/lib/mapData.ts despike 와 같은 규칙: 혼자 툭 튀어나왔다 돌아오는 점을 뺀다."""
    if len(pts) < 3:
        return pts
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        a, b, c = out[-1], pts[i], pts[i + 1]
        if dist(a, b) + dist(b, c) > dist(a, c) * 2.5 + 40:
            continue
        out.append(b)
    out.append(pts[-1])
    return out


def course_points(place):
    """화면이 코스 선으로 그리는 점들(get_place_detail 의 all_points, '(=n)' 되돌아온 기록 제외)."""
    d = T.get_place_detail(place)
    pts = [(p["lat"], p["lon"]) for p in d.get("all_points", [])
           if not str(p.get("label", "")).startswith("(=") and p.get("lat") is not None]
    return despike(pts)


def osrm(pts):
    coords = ";".join(f"{lon:.6f},{lat:.6f}" for lat, lon in pts)
    url = f"{OSRM}{coords}?overview=false&steps=true&geometries=geojson"
    req = urllib.request.Request(url, headers={"User-Agent": "jeju-gachi-route-build/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def snapped_runs(pts):
    """구간마다 길 모양(믿을 만할 때) 또는 직선. 같은 종류끼리 이어 [[길이면 1·직선이면 0, [[위도, 경도], ...]], ...].
    조사 지점은 그대로 선 위에 남긴다(구간 양 끝)."""
    res = osrm(pts)
    if res.get("code") != "Ok":
        return None, 0
    wps, legs = res["waypoints"], res["routes"][0]["legs"]
    runs, used = [], 0
    for i, leg in enumerate(legs):
        a, b = pts[i], pts[i + 1]
        road = (wps[i]["distance"] <= SNAP_M and wps[i + 1]["distance"] <= SNAP_M
                and 0 < leg["distance"] <= dist(a, b) * DETOUR + SLACK_M)
        seg = [a]
        if road:
            for st in leg["steps"]:
                for lon, lat in st["geometry"]["coordinates"]:
                    if dist(seg[-1], (lat, lon)) > 0.5:
                        seg.append((lat, lon))
            used += 1
        if dist(seg[-1], b) > 0.5:
            seg.append(b)
        if runs and runs[-1][0] == int(road):
            runs[-1][1].extend(seg[1:])
        else:
            runs.append([int(road), seg])
    return runs, used


def main():
    d = T.load()
    places = [p for p in d["places"]["place"] if not T.is_tour(d["places"][d["places"]["place"] == p].iloc[0])]
    out, legs_all, legs_used = {}, 0, 0
    for n, place in enumerate(places, 1):
        pts = course_points(place)
        if len(pts) < 2:
            continue
        try:
            runs, used = snapped_runs(pts)
        except Exception as e:  # 길찾기를 못 받으면 그 장소는 지금처럼 직선
            print(f"[{n}/{len(places)}] {place}: 실패 {e}")
            runs, used = None, 0
        legs_all += len(pts) - 1
        legs_used += used
        if runs and used:
            out[place] = [[road, [[round(lat, 6), round(lon, 6)] for lat, lon in seg]] for road, seg in runs]
        print(f"[{n}/{len(places)}] {place}: 구간 {len(pts) - 1}개 중 길 모양 {used}개")
        time.sleep(1)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"저장 {OUT} · 장소 {len(out)}곳 · 구간 {legs_all}개 중 길 모양 {legs_used}개")


if __name__ == "__main__":
    main()
