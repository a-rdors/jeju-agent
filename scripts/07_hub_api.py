"""제주데이터허브 OpenAPI(프로젝트 키 필요)로 버스 정류소·약국 정보를 받아 정리한다.

입력: .env 의 JEJU_PROJECT_KEY (마이페이지 > 프로젝트 관리 > 해당 프로젝트의 키)
      프로젝트에 '버스 정류소 기본 정보', '약국 정보' 데이터를 담아 두어야 한다.
출력:
  data/raw/hub/bus_stations.json, pharmacy.json   API 원본(페이지를 합친 것)
  data/processed/bus_stops.csv                     정류소 이름·주변 표시·방향·좌표
  data/processed/pharmacy_status.csv               약국 영업 상태(영업/정상, 휴업, 폐업)와 주소

요청 주소 형식은 각 데이터의 API 가이드 문서(HWP)를 따른다:
  https://open.jejudatahub.net/api/proxy/{데이터키}/{프로젝트키}?number=페이지&limit=100
키 값은 화면이나 파일에 남기지 않는다.
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "hub"
PROC = ROOT / "data" / "processed"
BASE = "https://open.jejudatahub.net/api/proxy"
UA = {"User-Agent": "Mozilla/5.0 (jeju-agent data download)"}

DATASETS = {
    "bus_stations": ("DD11ab6a6t11D16baaa1a2tD26ata161", "버스 정류소 기본 정보"),
    "pharmacy": ("taD8a8t1atabta1Dtt1tta6bt16ab16a", "약국 정보"),
}


def project_key() -> str:
    key = (dotenv_values(ROOT / ".env").get("JEJU_PROJECT_KEY") or "").strip()
    if not key:
        sys.exit(".env 에 JEJU_PROJECT_KEY 가 없어요.")
    return key


def fetch_all(data_key: str, key: str) -> list:
    """number=1,2,... 로 hasMore 가 끝날 때까지 받는다."""
    rows, page = [], 1
    while True:
        q = urllib.parse.urlencode({"number": page, "limit": 100})
        url = f"{BASE}/{data_key}/{key}?{q}"
        for attempt in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                    d = json.load(r)
                break
            except Exception as e:  # 키가 메시지에 섞이지 않게 종류만 보여 준다
                if attempt == 2:
                    sys.exit(f"  {page}쪽 요청 실패: {type(e).__name__} {getattr(e, 'code', '')}")
                time.sleep(2)
        rows += d.get("data") or []
        if not d.get("hasMore"):
            return rows
        page += 1
        time.sleep(0.2)


def build_bus(rows: list) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["lat"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["lon"] = pd.to_numeric(df["longitude"], errors="coerce")
    df = df[df["lat"].between(33.0, 34.0) & df["lon"].between(126.0, 127.1)]
    out = pd.DataFrame({
        "station_id": df["stationId"].astype(str),
        "name": df["stationName"].str.strip(),
        "local_info": df["localInfo"].fillna("").str.strip(),
        "direction": df["direction"].fillna("").str.strip(),
        "address": df["stationAddress"].fillna("").str.strip(),
        "lat": df["lat"], "lon": df["lon"],
    }).drop_duplicates("station_id")
    out["source"] = "제주데이터허브 버스 정류소 기본 정보"
    return out


def build_pharmacy(rows: list) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    out = pd.DataFrame({
        "name": df["companyName"].str.strip(),
        "open_status": df["openStatus"].fillna("").str.strip(),
        "licensing_date": df.get("licensingDate", "").astype(str),
        "close_date": df.get("closeDate", pd.Series([""] * len(df))).fillna("").astype(str),
        "address_doro": df.get("addressDoro", "").fillna(""),
        "address_jibun": df.get("addressJibun", "").fillna(""),
        "update_at": df.get("updateAt", "").fillna(""),
    })
    out["source"] = "제주데이터허브 약국 정보"
    return out


def main():
    key = project_key()
    RAW.mkdir(parents=True, exist_ok=True)
    got = {}
    for name, (data_key, title) in DATASETS.items():
        print(f"{title} 받는 중...")
        rows = fetch_all(data_key, key)
        (RAW / f"{name}.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        print(f"  {len(rows)}건")
        got[name] = rows

    bus = build_bus(got["bus_stations"])
    bus.to_csv(PROC / "bus_stops.csv", index=False, encoding="utf-8-sig")
    print(f"bus_stops.csv: {len(bus)}곳")

    ph = build_pharmacy(got["pharmacy"])
    ph.to_csv(PROC / "pharmacy_status.csv", index=False, encoding="utf-8-sig")
    print(f"pharmacy_status.csv: {len(ph)}곳  " + ", ".join(f"{k} {v}" for k, v in ph["open_status"].value_counts().items()))


if __name__ == "__main__":
    main()
