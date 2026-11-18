"""제주데이터허브 무장애여행일반정보 HWP 파일에서 사진과 주소를 추출한다.

출처 및 라이선스:
  - 데이터 제공: 제주특별자치도 미래성장과 (jejudatahub.net)
  - 데이터셋: 무장애여행일반정보 (카탈로그 ID: 1150~1200 범위)
  - 공개 여부: authYn=false (로그인 불필요 공개 데이터)
  - 저작물 이용 시 출처 표기 권장 (제주특별자치도 공공데이터)

의존성 (requirements.txt 미포함, 개발·전처리 전용):
  pip install olefile Pillow

입력:
  data/raw/mujangae/catalog.json         (01_download_mujangae.py 결과)
  data/processed/places_app.csv          (70개 나들이 장소)

출력:
  data/raw/mujangae/general_src/{id}.hwp  (HWP 원본 캐시)
  web/public/photos/<n>/<i>.jpg           (n=장소 행 인덱스, i=1~3, JPEG 최대 640px)
  data/processed/place_info.csv           (place, address, photos 열)

실행: python scripts/06_place_photos.py
"""
import csv
import io
import json
import re
import sys
import time
import urllib.request
import zlib
from pathlib import Path

import olefile
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "raw" / "mujangae" / "catalog.json"
PLACES_CSV = ROOT / "data" / "processed" / "places_app.csv"
HWP_CACHE = ROOT / "data" / "raw" / "mujangae" / "general_src"
PHOTOS_OUT = ROOT / "web" / "public" / "photos"
INFO_CSV = ROOT / "data" / "processed" / "place_info.csv"

BASE = "https://jejudatahub.net"
UA = {"User-Agent": "Mozilla/5.0 (jeju-agent data download)"}

# --- 이름 정규화 (공백·괄호 무시 매칭) ---

def normalize_name(name: str) -> str:
    """공백을 제거해 비교용 키를 만든다."""
    return re.sub(r"\s+", "", name).strip()


# --- 카탈로그 로딩 및 장소 매칭 ---

def load_catalog_map() -> dict:
    """catalog.json에서 일반정보 항목 50개를 (정규화 이름 -> entry) 사전으로 반환."""
    with open(CATALOG, encoding="utf-8") as f:
        catalog = json.load(f)
    result = {}
    for entry in catalog:
        if not entry["title"].endswith("_무장애여행일반정보"):
            continue
        place_name = entry["title"].rsplit("_무장애여행일반정보", 1)[0]
        result[normalize_name(place_name)] = entry
    return result


def load_places() -> list:
    """places_app.csv를 행 인덱스 순서 그대로 반환."""
    with open(PLACES_CSV, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


# --- HWP 다운로드 (캐시 우선) ---

def get_bytes_fi(file_info: dict) -> bytes:
    """fileInfo 객체로 jejudatahub 파일을 내려받는다."""
    url = f"{BASE}/api/file?id={file_info['id']}&fileId={file_info['fileId']}"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def download_hwp(entry: dict) -> Path | None:
    """HWP 원본을 캐시 폴더에 내려받고 경로를 반환. 실패 시 None."""
    df_infos = ((entry.get("dataFile") or {}).get("fileInfos") or [])
    if not df_infos:
        return None
    fi = df_infos[0]
    path = HWP_CACHE / f"{entry['id']}.hwp"
    if path.exists():
        return path
    try:
        data = get_bytes_fi(fi)
    except Exception as e:
        print(f"  [다운로드 오류] {entry['title']}: {e}")
        return None
    # OLE 매직 바이트 확인 (D0 CF 11 E0)
    if data[:4] != b"\xd0\xcf\x11\xe0":
        print(f"  [형식 오류] {entry['title']}: OLE 헤더 아님 ({data[:8].hex()})")
        return None
    path.write_bytes(data)
    time.sleep(0.3)
    return path


# --- PrvText에서 주소 추출 ---

def extract_address(prv_bytes: bytes) -> str:
    """HWP PrvText 스트림(UTF-16LE)에서 주소를 추출한다.

    패턴: <주소><제주 ... 주소 본문 ... - 내비게이션 안내 ...>
    첫 번째 ' - ' 이전을 주소로 취하고 '제주'로 시작하는지 검사한다.
    """
    text = prv_bytes.decode("utf-16-le", errors="replace")
    m = re.search(r"<주소><([^>]+)>", text)
    if not m:
        return ""
    addr = m.group(1).strip()
    # ' - 내비게이션' 등 안내 문구 이전만 취함
    addr = re.split(r"\s+-\s+", addr)[0].strip()
    if not addr.startswith("제주"):
        return ""
    return addr


# --- BinData 이미지 추출 및 선별 ---

def _try_open_image(raw: bytes) -> Image.Image | None:
    """바이트 데이터에서 PIL 이미지를 여러 방식으로 시도해 반환.

    HWP5의 BinData에는 세 가지 형식이 혼재한다:
    - JPEG / PNG: 직접 열기 가능
    - BMP: raw DEFLATE(wbits=-15)로 압축돼 있어 먼저 압축 해제 필요
    """
    # 직접 열기 시도 (JPEG, PNG, 비압축 BMP)
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
        return img
    except Exception:
        pass
    # raw DEFLATE 압축 해제 후 열기 (HWP BMP)
    try:
        decompressed = zlib.decompress(raw, -15)
        img = Image.open(io.BytesIO(decompressed))
        img.load()
        return img
    except Exception:
        pass
    return None


def extract_images(data: bytes) -> list[tuple]:
    """OLE 데이터에서 이미지(JPEG·PNG·BMP)를 추출, 픽셀 면적 내림차순으로 반환.

    반환: [(area, name, Image, raw_bytes), ...]  (100px 미만 제외)
    HWP5 BinData는 JPEG/PNG는 비압축, BMP는 raw DEFLATE 압축 형태로 저장된다.
    """
    ole = olefile.OleFileIO(io.BytesIO(data))
    images = []
    for entry in ole.listdir():
        if entry[0] != "BinData":
            continue
        path = "/".join(entry)
        raw = ole.openstream(path).read()
        img = _try_open_image(raw)
        if img is None:
            continue
        w, h = img.size
        if min(w, h) < 100:  # 아이콘·로고 제외 (HWP 내부 썸네일은 보통 170~354px)
            continue
        images.append((w * h, entry[-1], img, raw))
    ole.close()
    images.sort(key=lambda x: x[0], reverse=True)
    return images


def pick_representative(images: list, max_count: int = 3) -> list:
    """최대 max_count 장의 대표 이미지를 선택한다 (유사 중복 제외).

    중복 판단: 동일 픽셀 크기 AND 파일 크기 차이 5% 이내.
    """
    picked = []
    for area, name, img, raw in images:
        duplicate = any(
            img.size == p[2].size
            and abs(len(raw) - len(p[3])) <= len(raw) * 0.05
            for p in picked
        )
        if duplicate:
            continue
        picked.append((area, name, img, raw))
        if len(picked) >= max_count:
            break
    return picked


def save_image(
    img: Image.Image,
    out_path: Path,
    max_width: int = 640,
    quality: int = 78,
    max_bytes: int = 80 * 1024,
) -> int:
    """이미지를 max_width 이하로 리사이즈 후 JPEG로 저장.

    파일 크기가 max_bytes를 초과하면 quality를 낮춰 재시도한다.
    파일 크기(bytes) 반환.
    """
    if img.width > max_width:
        ratio = max_width / img.width
        new_size = (max_width, int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)
    if img.mode != "RGB":
        img = img.convert("RGB")

    for q in [quality, quality - 8, quality - 16, quality - 24]:
        q = max(q, 40)
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=q, optimize=True)
        data = buf.getvalue()
        if len(data) <= max_bytes or q <= 40:
            break

    out_path.write_bytes(data)
    return len(data)


# --- 메인 처리 ---

def main():
    HWP_CACHE.mkdir(parents=True, exist_ok=True)
    PHOTOS_OUT.mkdir(parents=True, exist_ok=True)

    print("데이터 출처: 제주특별자치도 미래성장과 / 제주데이터허브 (jejudatahub.net) 무장애여행일반정보")
    print("라이선스: 공공데이터 (authYn=false, 로그인 불필요 공개 데이터, 출처 표기 권장)\n")

    catalog_map = load_catalog_map()
    places = load_places()
    print(f"장소 수: {len(places)}, 카탈로그 일반정보: {len(catalog_map)}")

    # 매칭 결과
    unmatched_names = []
    matched_indices = []
    for idx, row in enumerate(places):
        key = normalize_name(row["place"])
        if key in catalog_map:
            matched_indices.append((idx, row["place"], catalog_map[key]))
        else:
            unmatched_names.append(f"{idx}: {row['place']}")

    print(f"매칭 성공: {len(matched_indices)}, 미매칭: {len(unmatched_names)}")
    if unmatched_names:
        print("미매칭 장소:")
        for u in unmatched_names:
            print(f"  {u}")
    print()

    # 결과 저장용: place -> (address, photos_list)
    info: dict[str, dict] = {}

    got_photos = 0
    got_address = 0
    total_bytes = 0

    for idx, place_name, entry in matched_indices:
        print(f"[{idx:02d}] {place_name} ...", end=" ", flush=True)

        # HWP 다운로드 (캐시 우선)
        hwp_path = download_hwp(entry)
        if hwp_path is None:
            print("(HWP 다운로드 실패)")
            info[place_name] = {"address": "", "photos": []}
            continue

        ole_data = hwp_path.read_bytes()

        # 주소 추출
        address = ""
        try:
            ole = olefile.OleFileIO(io.BytesIO(ole_data))
            if ole.exists("PrvText"):
                prv_bytes = ole.openstream("PrvText").read()
                address = extract_address(prv_bytes)
            ole.close()
        except Exception as e:
            print(f"(PrvText 오류: {e})", end=" ")

        # 이미지 추출
        photos_urls = []
        try:
            images = extract_images(ole_data)
            selected = pick_representative(images, max_count=3)
            if selected:
                place_dir = PHOTOS_OUT / str(idx)
                place_dir.mkdir(parents=True, exist_ok=True)
                for img_i, (area, name, img, raw) in enumerate(selected, start=1):
                    out_path = place_dir / f"{img_i}.jpg"
                    sz = save_image(img, out_path)
                    total_bytes += sz
                    photos_urls.append(f"/photos/{idx}/{img_i}.jpg")
        except Exception as e:
            print(f"(이미지 오류: {e})", end=" ")

        if address:
            got_address += 1
        if photos_urls:
            got_photos += 1

        print(f"주소={'있음' if address else '없음'}, 사진={len(photos_urls)}장")
        info[place_name] = {"address": address, "photos": photos_urls}

    # 미매칭 장소도 빈 행으로 추가
    for idx, row in enumerate(places):
        if row["place"] not in info:
            info[row["place"]] = {"address": "", "photos": []}

    # place_info.csv 저장 (places_app.csv 순서 유지)
    with open(INFO_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["place", "address", "photos"])
        for row in places:
            name = row["place"]
            d = info[name]
            w.writerow([name, d["address"], "|".join(d["photos"])])

    print(f"\n완료: 사진 {got_photos}/{len(matched_indices)}곳, 주소 {got_address}/{len(matched_indices)}곳")
    print(f"web/public/photos 총 용량: {total_bytes / 1024:.1f} KB")
    print(f"place_info.csv 저장: {INFO_CSV}")


if __name__ == "__main__":
    main()
