"""대규모 시뮬레이션: 데이터·도구 전수 점검(A) + 여러 상황을 조합한 질문으로 Agent 점검(B).

A. 데이터·도구(AI 없음, 전수)
   - 장소 추천: 이동 유형 6 × 동네 13 × 분위기 7
   - 장소 상세·근처 병원/약국/화장실: 장소 247곳 전부
   - 식당: 종류 7(없음 포함) × 식사 조건 8(없음 포함) × 기준 9
   점검: 오류 없음, 빈 값·'nan' 없음, 좌표가 제주 안, 전화번호 형식, 가게 이름에 ';'·구내식당 없음
B. Agent(AI, 조합 질문 약 180개, 고정 시드로 매번 같은 질문)
   누구(이동 유형·없음) × 어디(동네·공항·시장·없음) × 무엇(장소·식당·병원·날씨·일정·이어서·막연·범위 밖·줄임말)
   점검: 오류 없음 · 필요한 도구 · 답변 형식 · 근거(지어낸 이름 없음) · 동네 지킴 · '장애인'을 말하지 않았으면 쓰지 않음 · 응답 시간

실행: python scripts/08_simulation.py [--only A|B] [--n 180]
결과: docs/대규모_시뮬레이션.md, docs/simulation_results.json
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import importlib
import json
import math
import random
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
broad = importlib.import_module("07_broad_test")
base = importlib.import_module("04_scenario_test")
A, T = base.A, base.T if hasattr(base, "T") else importlib.import_module("tools")
grounded, check_format, EMOJI = base.grounded, broad.check_format, broad.EMOJI

JEJU = (33.10, 33.60, 126.10, 127.00)
PHONE = re.compile(r"^(0\d{1,2}-\d{3,4}-\d{4}|0\d{3}-\d{3,4}-\d{4}|1\d{3}-\d{4}|010-\d{4}-\d{4})$")
NAN = re.compile(r"(^|\W)nan($|\W)|None|null분|undefined")


def in_jeju(lat, lon):
    return lat is not None and lon is not None and JEJU[0] <= float(lat) <= JEJU[1] and JEJU[2] <= float(lon) <= JEJU[3]


def scan_text(obj, path="", out=None):
    """결과 안의 글자에 'nan'·'None'이 그대로 찍혀 있는지(화면에 그대로 보이는 값)"""
    out = [] if out is None else out
    if isinstance(obj, dict):
        for k, v in obj.items():
            scan_text(v, f"{path}.{k}", out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:20]):
            scan_text(v, f"{path}[{i}]", out)
    elif isinstance(obj, str) and NAN.search(obj):
        out.append(f"{path}='{obj[:40]}'")
    elif isinstance(obj, float) and math.isnan(obj):
        out.append(f"{path}=NaN")
    return out


# ============================== A. 데이터·도구 ==============================
AREAS = [None, "제주시", "서귀포", "애월", "한림", "중문", "성산", "함덕", "표선", "구좌", "대정", "안덕", "조천"]
THEMES = [None, "바다", "마을", "자연·숲", "역사·문화", "실내", "시장"]


def part_a():
    probs, stats = [], {"추천": 0, "추천 결과 없음": 0, "장소 상세": 0, "근처 도움": 0, "식당": 0, "식당 결과 없음": 0}
    # 1) 장소 추천 전수
    for ut in T.USER_TYPES:
        for area in AREAS:
            for theme in THEMES:
                tag = f"추천 {ut}/{area}/{theme}"
                try:
                    r = T.recommend_places(user_type=ut, area=area, theme=theme)
                except Exception as e:
                    probs.append((tag, f"오류 {type(e).__name__}: {e}"))
                    continue
                stats["추천"] += 1
                rs = r.get("results") or []
                if not rs:
                    stats["추천 결과 없음"] += 1
                for x in rs:
                    if not in_jeju(x.get("lat"), x.get("lon")):
                        probs.append((tag, f"{x['place']} 좌표가 제주 밖"))
                    if not x.get("verdict"):
                        probs.append((tag, f"{x['place']} 판정 없음"))
                    if x.get("phone") and not PHONE.match(x["phone"]):
                        probs.append((tag, f"{x['place']} 전화번호 형식 '{x['phone']}'"))
                    bad = scan_text({k: x.get(k) for k in ("place", "where", "verdict", "verdict_reason", "slope_say", "good_points", "watch_out")})
                    if bad:
                        probs.append((tag, f"{x['place']} 빈 값 {bad[:2]}"))
    # 2) 장소 상세·근처 도움 전수
    places = list(T.load()["places"]["place"])

    def one_place(p):
        out = []
        try:
            d = T.get_place_detail(p, "manual_wheelchair")
            if "error" in d:
                out.append((f"상세 {p}", d["error"]))
            else:
                out += [(f"상세 {p}", b) for b in scan_text({k: d.get(k) for k in ("where", "verdict", "verdict_reason", "slope_say")})[:2]]
                for t in d.get("toilets_near") or []:
                    if t.get("phone") and not PHONE.match(t["phone"]):
                        out.append((f"상세 {p}", f"화장실 전화번호 형식 '{t['phone']}'"))
        except Exception as e:
            out.append((f"상세 {p}", f"오류 {type(e).__name__}: {e}"))
        try:
            h = T.find_nearby_help(p)
            if "error" in h:
                out.append((f"도움 {p}", h["error"]))
            else:
                if not (h["help"].get("응급실")):
                    out.append((f"도움 {p}", "응급실 없음"))
                for kind, items in h["help"].items():
                    for it in items:
                        if it.get("km") is None or it["km"] > 60:
                            out.append((f"도움 {p}", f"{kind} {it['name']} 거리 이상 {it.get('km')}"))
                        if it.get("phone") and not PHONE.match(it["phone"]):
                            out.append((f"도움 {p}", f"{kind} {it['name']} 전화번호 형식 '{it['phone']}'"))
                        if not in_jeju(it.get("lat"), it.get("lon")):
                            out.append((f"도움 {p}", f"{kind} {it['name']} 좌표가 제주 밖"))
        except Exception as e:
            out.append((f"도움 {p}", f"오류 {type(e).__name__}: {e}"))
        return out

    with cf.ThreadPoolExecutor(8) as ex:
        for res in ex.map(one_place, places):
            probs += res
    stats["장소 상세"] = stats["근처 도움"] = len(places)
    # 3) 식당 전수
    anchors = [("area", "제주시"), ("area", "서귀포"), ("area", "애월"), ("area", "성산"), ("place", "제주공항"),
               ("place", "중문관광단지"), ("place", "감귤박물관"), ("place", "동문시장"), ("area", None)]
    kinds = [None] + list(T.FOOD_KINDS)
    diets = [None] + list(T.DIET_NEEDS)
    jobs = [(k, dn, a) for k in kinds for dn in diets for a in anchors]

    def one_food(job):
        k, dn, (key, val) = job
        tag = f"식당 {k}/{dn}/{val}"
        out, empty = [], False
        try:
            f = T.search_food(food_kind=k, diet_needs=[dn] if dn else None, limit=5, **({key: val} if val else {}))
            items = f.get("items") or []
            empty = not items and not f.get("anchor_not_found")
            if f.get("anchor_not_found"):
                out.append((tag, f"기준을 못 찾음: {f.get('note', '')[:40]}"))
            for it in items:
                n = str(it.get("name", ""))
                if ";" in n:
                    out.append((tag, f"이름에 ';' {n}"))
                if re.search(T.NOT_RESTAURANT, n):
                    out.append((tag, f"구내식당·기관 이름 {n}"))
                if it.get("phone") and not PHONE.match(it["phone"]):
                    out.append((tag, f"{n} 전화번호 형식 '{it['phone']}'"))
                if not in_jeju(it.get("lat"), it.get("lon")):
                    out.append((tag, f"{n} 좌표가 제주 밖"))
                out += [(tag, f"{n} 빈 값 {b}") for b in scan_text({"type": it.get("food_type"), "floor": it.get("floor_note")})[:1]]
        except Exception as e:
            out.append((tag, f"오류 {type(e).__name__}: {e}"))
        return out, empty

    with cf.ThreadPoolExecutor(8) as ex:
        for res, empty in ex.map(one_food, jobs):
            probs += res
            stats["식당"] += 1
            stats["식당 결과 없음"] += empty
    # 4) 일상어 바꾸기
    s = T.neutral_words("장애인 화장실과 장애인 주차구역이 있고 휠체어로 들어가기 편해요. 제주올레길1코스(휠체어구간)", "senior")
    if "장애인" in s or "휠체어로" in s or "(휠체어구간)" not in s:
        probs.append(("일상어", s))
    return stats, probs


# ============================== B. Agent ==============================
WHO = [  # (말, 이동 유형 짐작, 휠체어·장애를 말했는지)
    ("휠체어 타는 아빠", "wheel", True), ("전동휠체어 쓰는 엄마", "wheel", True), ("휠체어 타는 동생", "wheel", True),
    ("유모차 탄 아기", "stroller", False), ("돌 지난 아기", "stroller", False), ("무릎이 안 좋은 할머니", "senior", False),
    ("거동이 불편한 할아버지", "senior", False), ("부모님", "senior", False), ("임신 7개월 아내", "pregnant", False),
    ("", None, False),
]
WHERE = [  # (말, 기준 이름 또는 시, 종류)
    ("제주시", "제주시", "city"), ("서귀포", "서귀포시", "city"), ("애월", "애월", "area"), ("한림", "한림", "area"),
    ("중문", "중문", "area"), ("성산", "성산", "area"), ("함덕", "함덕", "area"), ("표선", "표선", "area"),
    ("공항 근처", "제주공항", "landmark"), ("동문시장 근처", "동문시장", "place"), ("", None, None),
]
PLACE_ASK = ["바다 보러 갈 만한 데 있어?", "숲길 산책할 곳 추천해줘", "비 오는 날 실내로 갈 곳", "박물관 가고 싶어",
             "가볍게 바람 쐬러 갈 곳", "경사 없는 산책로 알려줘"]
FOOD_ASK = ["흑돼지 먹을 데", "국수 먹고 싶어", "해산물 식당 알려줘", "부드러운 음식 먹을 곳", "속 편한 순한 음식",
            "안 매운 밥집", "카페 가고 싶어", "짜지 않게 먹을 곳"]
HELP_ASK = ["약국 어디 있어?", "병원 가야 해", "응급실 어디야?", "화장실 급해", "기저귀 갈 곳 있어?"]
FOLLOW = [(["{who}랑 {where} 갈 만한 곳"], "거기 화장실은 어디쯤 있어?", "any", {"get_place_detail", "find_nearby_help"}),
          (["{who}랑 {where} 갈 만한 곳"], "다른 곳은 없어?", "place", {"recommend_places"}),
          (["{who}랑 {where} 갈 만한 곳"], "그 근처 밥집도 알려줘", "food", {"search_food"}),
          (["{who}랑 {where} 갈 만한 곳"], "거기 근처 약국은?", "help", {"find_nearby_help"})]
SCOPE = ["서울에서 갈 만한 곳 알려줘", "묵을 숙소 추천해줘", "제주에서 제일 맛있는 집 1위", "감기약 먹어도 돼?",
         "식당 예약 좀 해줘", "렌터카 어디서 빌려?", "비행기표 예매해줘"]
VAGUE = ["어디 갈 만한 데 있어?", "추천해줘", "놀러 갈 곳"]
SLANG = [("휠체어 바다 ㄱㄱ", "place", {"recommend_places"}), ("할매랑 밥 어디서 먹지 제주시", "food", {"search_food"}),
         ("유모차 카패 서귀포", "food", {"search_food"}), ("애기랑 실내 ㄱ", "place", {"recommend_places"}),
         ("할배 약국 급함 중문", "help", {"find_nearby_help"})]


def rang(who):
    """'동생' → '동생이랑', '아빠' → '아빠랑'"""
    if not who:
        return ""
    last = who[-1]
    has = "가" <= last <= "힣" and (ord(last) - 0xAC00) % 28 != 0
    return who + ("이랑" if has else "랑")


def join(*parts):
    return " ".join(p for p in parts if p).replace("  ", " ").strip()


def build_cases(n, seed=7):
    rnd = random.Random(seed)
    cases = []
    while len(cases) < n:
        kind = rnd.choices(["place", "food", "help", "weather", "plan", "follow", "scope", "vague", "slang"],
                           weights=[24, 22, 14, 8, 8, 10, 7, 3, 4])[0]
        who, ut, said_disab = rnd.choice(WHO)
        where, anchor, wkind = rnd.choice(WHERE)
        w = rang(who)
        if kind == "place":
            q = join(w, where.replace(" 근처", " 근처에서") if wkind == "landmark" else (f"{where}에서" if where else ""), rnd.choice(PLACE_ASK))
            cases.append(dict(cat="장소", qs=[q], tools={"recommend_places", "ask_user"}, fmt="place", who=ut, disab=said_disab, anchor=anchor, wkind=wkind))
        elif kind == "food":
            q = join(w, where, rnd.choice(FOOD_ASK))
            cases.append(dict(cat="식당", qs=[q], tools={"search_food", "ask_user"}, fmt="food", who=ut, disab=said_disab, anchor=anchor, wkind=wkind))
        elif kind == "help":
            if not where:
                where, anchor, wkind = "감귤박물관 근처", "감귤박물관", "place"
            q = join(where, rnd.choice(HELP_ASK), f"({who} 동행)" if who else "")
            cases.append(dict(cat="병원·약국·화장실", qs=[q], tools={"find_nearby_help", "ask_user", "get_place_detail"}, fmt="help", who=ut, disab=said_disab, anchor=anchor, wkind=wkind))
        elif kind == "weather":
            q = join(rnd.choice(["내일", "주말에", "모레"]), w, where, rnd.choice(["바다 가도 될까?", "나들이 가도 괜찮을까?", "산책 가도 돼?"]))
            cases.append(dict(cat="날씨", qs=[q], tools={"recommend_places", "get_weather"}, fmt="place", who=ut, disab=said_disab, anchor=anchor, wkind=wkind))
        elif kind == "plan":
            q = join(w, where, rnd.choice(["반나절 코스 짜줘", "하루 일정 짜줘", "가볍게 동선 짜줘"]))
            cases.append(dict(cat="일정", qs=[q], tools={"plan_outing", "ask_user"}, fmt="plan", who=ut, disab=said_disab, anchor=anchor, wkind=wkind))
        elif kind == "follow":
            if not who:
                who, ut, said_disab = WHO[0]
            first, second, fmt, tools = rnd.choice(FOLLOW)
            q1 = first[0].replace("{who}랑", rang(who)).format( where=f"{where}에서" if where and wkind != "landmark" else (where or "제주에서")).replace("  ", " ")
            cases.append(dict(cat="이어서", qs=[q1, second], tools=tools, fmt=fmt, who=ut, disab=said_disab, anchor=None, wkind=None))
        elif kind == "scope":
            q = join(w, rnd.choice(SCOPE))
            cases.append(dict(cat="범위 밖", qs=[q], tools=set(), fmt="scope", who=ut, disab=said_disab, anchor=None, wkind=None))
        elif kind == "vague":
            cases.append(dict(cat="막연", qs=[rnd.choice(VAGUE)], tools={"ask_user"}, fmt="ask", who=None, disab=False, anchor=None, wkind=None))
        else:
            q, fmt, tools = rnd.choice(SLANG)
            cases.append(dict(cat="줄임말", qs=[q], tools=tools, fmt=fmt, who=None, disab="휠체어" in q, anchor=None, wkind=None))
    # 같은 질문 중복 제거
    seen, uniq = set(), []
    for c in cases:
        key = " / ".join(c["qs"])
        if key not in seen:
            seen.add(key)
            uniq.append(c)
    return uniq


def area_ok(c, out):
    """동네를 말했으면 그 동네(또는 시) 안에서 찾았는지"""
    if not c.get("anchor"):
        return True, ""
    if out.get("ask"):  # 시 이름만 말한 병원·약국 질문은 되묻는 것이 맞다
        return True, ""
    for name, args, res in out["tool_results"]:
        if not isinstance(res, dict):
            continue
        if name == "recommend_places" and res.get("results"):
            top = res["results"][0]
            if c["wkind"] == "city":
                if c["anchor"][:2] not in str(top.get("where", "")):
                    return False, f"{c['anchor']}인데 {top['place']}({top.get('where')})"
            elif top.get("distance_km") is not None and top["distance_km"] > 15:
                return False, f"{c['anchor']}에서 {top['distance_km']}km 떨어진 {top['place']}"
        if name == "search_food" and res.get("items"):
            around = str(res.get("around", ""))
            if c["wkind"] in ("landmark", "place", "area") and c["anchor"][:2] not in around and around != "제주 전체":
                pass
            if c["wkind"] in ("landmark", "area", "place") and around == "제주 전체":
                return False, f"{c['anchor']}인데 제주 전체에서 찾음"
        if name == "find_nearby_help" and res.get("help") and c["wkind"] in ("landmark", "place", "area"):
            if c["anchor"][:2] not in str(res.get("place", "")) and res.get("place") != "현재 위치":
                return False, f"{c['anchor']} 기준이어야 하는데 {res.get('place')}"
    return True, ""


def run_one(c):
    history, known, last_place, shown, out = [], None, None, [], None
    t0 = time.time()
    try:
        for q in c["qs"]:
            history.append({"role": "user", "content": q})
            out = A.run(history, known, last_place, None, shown)
            for name, a, res in out["tool_results"]:
                if name == "recommend_places" and isinstance(res, dict) and res.get("results"):
                    known = a.get("user_type") or known
                    last_place = res["results"][0]["place"]
                    shown = list(dict.fromkeys(shown + [r["place"] for r in res["results"]]))
            history.append({"role": "assistant", "content": out["text"]})
    except Exception as e:
        return {**c, "tools": sorted(c["tools"]), "pass": False, "problems": [f"오류: {type(e).__name__}: {e}"], "answer": "",
                "used": [], "sec": round(time.time() - t0, 1)}
    sec = round(time.time() - t0, 1)
    used = [t["tool"] for t in out["trace"]]
    probs = []
    if c["fmt"] == "scope":
        if any(t in used for t in ("recommend_places", "search_food", "plan_outing")):
            probs.append("범위 밖인데 추천함")
    elif c["tools"] and not (set(used) & c["tools"]):
        probs.append(f"필요한 도구 안 씀({'·'.join(used) or '없음'})")
    asked = bool(out.get("ask"))
    fmt = "ask" if asked and c["fmt"] != "scope" else c["fmt"]
    if fmt != "any":
        probs += check_format(out["text"], fmt)
    elif EMOJI.search(out["text"]):
        probs.append("이모지")
    ok_g, bad = grounded(out)
    said_all = " ".join(c["qs"])
    bad = [b for b in bad if b not in said_all]  # 사용자가 질문에 직접 말한 기준 장소(예: 동문시장)는 지어낸 이름이 아니다
    ok_g = not bad
    if not ok_g:
        probs.append(f"근거 없음: {', '.join(bad)}")
    ok_a, why = area_ok(c, out)
    if not ok_a:
        probs.append(f"동네 안 지킴: {why}")
    said = " ".join(c["qs"])
    if not re.search(r"장애|휠체어", said) and "장애인" in out["text"]:
        probs.append("말하지 않았는데 '장애인'")
    if not out["text"].strip():
        probs.append("빈 답")
    if sec > 45:
        probs.append(f"느림 {sec}초")
    return {**c, "tools": sorted(c["tools"]), "pass": not probs, "problems": probs, "answer": out["text"], "used": used,
            "asked": asked, "sec": sec}


def part_b(n, workers=6):
    cases = build_cases(n)
    rows = []
    with cf.ThreadPoolExecutor(workers) as ex:
        for r in ex.map(run_one, cases):
            rows.append(r)
            print(("OK " if r["pass"] else "XX ") + r["cat"], "|", " → ".join(r["qs"])[:46], "|", ">".join(r["used"]),
                  "|", "; ".join(r["problems"])[:120], flush=True)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["A", "B"])
    ap.add_argument("--n", type=int, default=180)
    args = ap.parse_args()
    docs = ROOT / "docs"
    lines = ["# 대규모 시뮬레이션", "", f"실행: {dt.datetime.now():%Y-%m-%d %H:%M} · 모델: {A.MODEL}", ""]
    result = {}
    if args.only != "B":
        t0 = time.time()
        stats, probs = part_a()
        result["A"] = {"stats": stats, "problems": probs}
        print("A 끝", stats, "문제", len(probs), f"{time.time() - t0:.0f}초")
        lines += ["## A. 데이터·도구 전수 점검(AI 없음)", "",
                  "| 항목 | 실행 수 |", "|---|---|"] + [f"| {k} | {v} |" for k, v in stats.items()] + \
                 ["", f"문제 {len(probs)}건", ""] + [f"- {t}: {p}" for t, p in probs[:200]] + [""]
    if args.only != "A":
        rows = part_b(args.n)
        result["B"] = rows
        ok = sum(r["pass"] for r in rows)
        by = {}
        for r in rows:
            by.setdefault(r["cat"], [0, 0])
            by[r["cat"]][0] += r["pass"]
            by[r["cat"]][1] += 1
        secs = sorted(r["sec"] for r in rows)
        med = secs[len(secs) // 2] if secs else 0
        print(f"B 통과 {ok}/{len(rows)}", by, f"응답 시간 중앙값 {med}초")
        lines += ["## B. Agent 조합 질문", "", f"통과 {ok}/{len(rows)} · 응답 시간 중앙값 {med}초 · 가장 긴 응답 {secs[-1] if secs else 0}초", "",
                  "점검: 오류 없음 · 필요한 도구 · 답변 형식 · 근거(지어낸 이름 없음) · 동네 지킴 · '장애인'을 말하지 않았으면 쓰지 않음 · 45초 이내", "",
                  "| 분류 | 통과 |", "|---|---|"] + [f"| {k} | {v[0]}/{v[1]} |" for k, v in by.items()] + \
                 ["", "| 결과 | 분류 | 질문 | 사용 도구 | 문제 |", "|---|---|---|---|---|"]
        for r in rows:
            lines.append(f"| {'통과' if r['pass'] else '실패'} | {r['cat']} | {' → '.join(r['qs'])} | {' → '.join(r['used'])} | "
                         f"{'; '.join(r['problems'])} |")
        lines += ["", "## 실패한 질문의 답변 원문", ""]
        for r in rows:
            if not r["pass"]:
                lines += [f"**[{r['cat']}] {' → '.join(r['qs'])}**", "", (r["answer"] or "").strip(), ""]
    (docs / "simulation_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=1, default=list), encoding="utf-8")
    (docs / "대규모_시뮬레이션.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
