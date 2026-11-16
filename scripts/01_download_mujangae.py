"""제주데이터허브 공개 카탈로그에서 무장애 여행 데이터를 내려받는다.

- 카탈로그(https://jejudatahub.net/api/data)에서 제목에 '무장애'가 들어간 데이터를 찾는다.
- 로그인 없이 공개된(authYn=false) 장소별 위치정보·주변정보 CSV와 일반정보 미리보기 CSV를 받는다.
- 결과: data/raw/mujangae/{kind}/{장소명}.csv, data/raw/mujangae/catalog.json

실행: python scripts/01_download_mujangae.py
"""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "mujangae"
BASE = "https://jejudatahub.net"
UA = {"User-Agent": "Mozilla/5.0 (jeju-agent data download)"}

KIND = {
    "무장애여행위치정보": ("location", "dataFile"),
    "무장애여행주변정보": ("nearby", "dataFile"),
    "무장애여행일반정보": ("general", "file"),  # 본 파일은 HWP라 표 형식 미리보기 CSV를 사용
}


def get_json(path, params=None):
    url = BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
        return json.load(r)


def get_bytes(file_info):
    url = f"{BASE}/api/file?id={file_info['id']}&fileId={file_info['fileId']}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def decode(b):
    for enc in ("utf-8-sig", "cp949"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            pass
    return b.decode("utf-8", "replace")


def fetch_catalog():
    rows, page = {}, 0
    while True:
        params = dict(includedKeywords="", excludedKeywords="", categories="", dataType="",
                      orderBy="createAt", userId="", authYn="false", autoUpdateYn="false",
                      keyword="무장애", keywordOrTagFlag="", isPaging="true",
                      start=page * 100, pageNumber=page + 1, length=100)
        data = get_json("/api/data", params)
        items = data if isinstance(data, list) else next((v for v in data.values() if isinstance(v, list)), [])
        new = [x for x in items if x["id"] not in rows]
        for x in items:
            rows[x["id"]] = x
        if not new:
            return list(rows.values())
        page += 1
        time.sleep(0.5)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    catalog = [x for x in fetch_catalog() if "무장애" in x["title"]]
    (OUT / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"카탈로그 무장애 데이터 {len(catalog)}건")

    saved = {k: 0 for k, _ in KIND.values()}
    for x in catalog:
        suffix = x["title"].split("_")[-1]
        if suffix not in KIND or x.get("authYn"):
            continue
        kind, key = KIND[suffix]
        place = x["title"].rsplit("_", 1)[0]
        infos = [f for f in ((x.get(key) or {}).get("fileInfos") or []) if f["fileName"].lower().endswith(".csv")]
        if not infos:
            continue
        target = OUT / kind / f"{place}.csv"
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_text(decode(get_bytes(infos[0])), encoding="utf-8")
            time.sleep(0.3)
        saved[kind] += 1
    print("저장:", saved)


if __name__ == "__main__":
    main()
