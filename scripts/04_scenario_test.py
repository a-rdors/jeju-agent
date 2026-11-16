"""시나리오 테스트: 실제 가족이 할 법한 막연한 질문 10개로 Agent를 돌리고 자동 채점한다.

채점 기준
1. 도구: 이 질문에 꼭 필요한 도구를 불렀는가
2. 조건: 추천 결과가 사용자가 말한 조건을 지켰는가
3. 근거: 답변에 나온 장소·가게 이름이 모두 도구 결과 안에 있는가(지어내지 않았는가)

실행: python scripts/04_scenario_test.py   (OPENAI_API_KEY 필요, 질문당 AI 호출 비용 발생)
결과: docs/시나리오_테스트.md, docs/scenario_results.json
"""
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
import agent as A  # noqa: E402
import tools as T  # noqa: E402

PLACES = set(T.load()["places"]["place"])
FOOD_NAMES = set(T.load()["food"]["name"]) | set(T.load()["nearby"]["name"])


def results_of(out, tool):
    return [res for name, _, res in out["tool_results"] if name == tool]


def args_of(out, tool):
    return [a for name, a, _ in out["tool_results"] if name == tool] + \
           [t["args"] for t in out["trace"] if t["tool"] == tool and tool == "ask_user"]


def grounded(out):
    """답변에 등장한 장소·가게 이름이 도구 결과에 있는지."""
    text = out["text"]
    allowed = set()
    for name, _, res in out["tool_results"]:
        for key in ("results", "items", "unverified", "stops"):
            for it in res.get(key, []) if isinstance(res, dict) else []:
                allowed.add(it.get("place") or it.get("name"))
        if isinstance(res, dict) and res.get("place"):
            allowed.add(res["place"])
        if isinstance(res, dict) and res.get("around"):  # 근처 검색의 기준(사용자가 말한 가게·동네)
            allowed.add(res["around"])
        if isinstance(res, dict) and isinstance(res.get("help"), dict):
            for items in res["help"].values():
                allowed |= {i["name"] for i in items}
    mentioned = {p for p in PLACES if p in text}
    if any(name == "search_food" for name, _, _ in out["tool_results"]):  # 가게 이름 검사는 식당 찾기를 했을 때만
        mentioned |= {f for f in FOOD_NAMES if len(f) >= 4 and f in text}  # 3글자 이하는 일반 단어와 겹침(예: 카페라서)
    bad = sorted(m for m in mentioned if not any(m in a or a in m for a in allowed if a))
    return (not bad), bad


def top(out):
    r = results_of(out, "recommend_places")
    return r[-1]["results"] if r else []


SCENARIOS = [
    {"id": 1, "q": ["어디 갈 만한 데 있어?"],
     "expect": "누가 가는지 모르므로 버튼으로 되묻기",
     "check": lambda o: (o["ask"] is not None, "되물음" if o["ask"] else "되묻지 않음")},
    {"id": 2, "q": ["아빠가 휠체어 타시는데 주말에 바다 보러 갈 만한 데 있어?"],
     "expect": "주말 날씨 확인 + 휠체어 기준 바다 장소",
     "check": lambda o: (bool(results_of(o, "get_weather")) and bool(top(o)) and "바다" in top(o)[0]["themes"],
                         f"날씨 {'O' if results_of(o, 'get_weather') else 'X'}, 1순위 {top(o)[0]['place'] if top(o) else '-'}")},
    {"id": 3, "q": ["유모차 끌고 애월 쪽 산책하고 싶어"],
     "expect": "유모차 기준, 애월에서 가까운 곳",
     "check": lambda o: (bool(top(o)) and (top(o)[0]["distance_km"] or 99) <= 10,
                         f"1순위 {top(o)[0]['place']} {top(o)[0]['distance_km']}km" if top(o) else "추천 없음")},
    {"id": 4, "q": ["할머니 모시고 가는데 화장실 걱정 없는 곳으로"],
     "expect": "어르신 기준, 장애인 화장실 있는 곳",
     "check": lambda o: (bool(top(o)) and top(o)[0]["accessible_toilet"],
                         f"1순위 {top(o)[0]['place']}, 화장실 {top(o)[0]['accessible_toilet']}" if top(o) else "추천 없음")},
    {"id": 5, "q": ["비 오는 날 전동 휠체어로 갈 만한 실내 있을까"],
     "expect": "전동 휠체어 기준 실내 장소",
     "check": lambda o: (bool(top(o)) and "실내" in top(o)[0]["themes"],
                         f"1순위 {top(o)[0]['place']} ({top(o)[0]['themes']})" if top(o) else "추천 없음")},
    {"id": 6, "q": ["성산 근처 해산물 식당 알려줘. 엄마가 휠체어 타셔"],
     "expect": "제주 전체 식당 대상 해산물, 휠체어 진입 확인 가게가 상위 3곳 안에",
     "check": lambda o: (bool(results_of(o, "search_food")) and any(i["wheelchair_entry"] for i in results_of(o, "search_food")[-1]["items"][:3]),
                         f"상위 {[(i['name'], i['wheelchair_entry']) for i in results_of(o, 'search_food')[-1]['items'][:3]]}" if results_of(o, "search_food") else "식당 도구 안 씀")},
    {"id": 7, "q": ["무릎 안 좋으신 어머니랑 숲길 잠깐 걷고 싶어"],
     "expect": "어르신 기준 숲 장소, 짧은 코스",
     "check": lambda o: (bool(top(o)) and "자연·숲" in top(o)[0]["themes"] and (top(o)[0]["minutes"] or 0) <= 45,
                         f"1순위 {top(o)[0]['place']} 약 {top(o)[0]['minutes']}분" if top(o) else "추천 없음")},
    {"id": 8, "q": ["휠체어로 갈 만한 데 추천해 줘", "거기 근처에 약국이나 병원 있어?"],
     "expect": "두 번째 질문에서 앞서 추천한 장소 기준으로 의료 찾기",
     "check": lambda o: (bool(results_of(o, "find_nearby_help")),
                         f"의료 찾기 기준 장소 {results_of(o, 'find_nearby_help')[-1]['place']}" if results_of(o, "find_nearby_help") else "의료 도구 안 씀")},
    {"id": 9, "q": ["서귀포 쪽에서 아기랑 갈 만한 곳"],
     "expect": "유모차 기준, 결과가 모두 서귀포시",
     "check": lambda o: (bool(top(o)) and all(r["where"].startswith("서귀포시") for r in top(o)),
                         ", ".join(r["where"] for r in top(o)) if top(o) else "추천 없음")},
    {"id": 10, "q": ["내일 바람 많이 불면 휠체어로 해안길 가도 괜찮을까?"],
     "expect": "내일 날씨 확인 후 바람 관련 판단",
     "check": lambda o: (bool(results_of(o, "get_weather")),
                         f"날씨 {results_of(o, 'get_weather')[-1].get('date')} 바람 {results_of(o, 'get_weather')[-1].get('wind_ms')}m/s" if results_of(o, "get_weather") else "날씨 안 봄")},
    {"id": 11, "q": ["아들이 휠체어를 타는데 이번에 제주도를 놀러가. 서귀포쪽으로 갈거같은데 가자마자 흑돼지를 먹고싶은데 맛집좀 알려줘",
                     "서귀포흑돈으로 갈거고 근처 카페좀 알려줘"],
     "expect": "(사용자 발견 버그 회귀) 두 번째 질문에서 '서귀포흑돈' 근처 카페를 찾음",
     "check": lambda o: (bool(results_of(o, "search_food")) and results_of(o, "search_food")[-1]["around"] == "서귀포흑돈"
                         and all((i["km"] or 99) <= 5 for i in results_of(o, "search_food")[-1]["items"]),
                         f"기준 {results_of(o, 'search_food')[-1]['around']}, 카페 {[i['name'] for i in results_of(o, 'search_food')[-1]['items']]}" if results_of(o, "search_food") else "식당 도구 안 씀")},
    {"id": 12, "q": ["이번에 제주도 왔는데 제주시로 왔어. 근데 할머니가 이가 안좋으셔서 마땅히 갈 식당이 없는데 어디갈까?"],
     "expect": "(사용자 발견) 씹기 불편한 어르신 → 부드러운 음식 식당",
     "check": lambda o: (bool(results_of(o, "search_food")) and "soft" in results_of(o, "search_food")[-1]["diet_needs"]
                         and bool(results_of(o, "search_food")[-1]["items"]),
                         f"조건 {results_of(o, 'search_food')[-1]['diet_needs']}, {[i['name'] for i in results_of(o, 'search_food')[-1]['items']][:3]}" if results_of(o, "search_food") else "식당 도구 안 씀")},
    {"id": 14, "q": ["5살 아이랑 할머니랑 애월에서 밥 먹을 건데 아이가 매운 걸 못 먹어"],
     "expect": "아이 동반·맵지 않은 음식 조건으로 애월 식당",
     "check": lambda o: (bool(results_of(o, "search_food")) and bool(set(results_of(o, "search_food")[-1]["diet_needs"]) & {"kids", "mild"})
                         and bool(results_of(o, "search_food")[-1]["items"]),
                         f"조건 {results_of(o, 'search_food')[-1]['diet_needs']}, 기준 {results_of(o, 'search_food')[-1]['around']}" if results_of(o, "search_food") else "식당 도구 안 씀")},
    {"id": 15, "q": ["휠체어 타는 아빠랑 서귀포에서 반나절 일정 짜줘. 아빠가 이가 안 좋으셔"],
     "expect": "일정 요청 → 장소 1곳 + 근처 씹기 편한 식당",
     "check": lambda o: (bool(results_of(o, "plan_outing")) and len(results_of(o, "plan_outing")[-1]["stops"]) >= 2
                         and [a for n, a, _ in o["tool_results"] if n == "plan_outing"][-1].get("diet_needs") == ["soft"],
                         f"일정 {[s_['name'] for s_ in results_of(o, 'plan_outing')[-1]['stops']]}" if results_of(o, "plan_outing") else "일정 도구 안 씀")},
    {"id": 16, "q": ["애월 근처 국수집 알려줘. 엄마가 휠체어 타셔"],
     "expect": "단순 식당 질문 → 일정 도구를 쓰지 않음",
     "check": lambda o: (bool(results_of(o, "search_food")) and not results_of(o, "plan_outing"),
                         f"도구 {[t['tool'] for t in o['trace']]}")},
    {"id": 17, "q": ["휠체어 타는 할머니랑 애월에서 카페 가고 싶어"],
     "expect": "(사용자 지적) 거동 불편 → 2층·지하 카페는 상위 3곳에서 빠짐",
     "check": lambda o: (bool(results_of(o, "search_food")) and bool(results_of(o, "search_food")[-1]["items"])
                         and all(i["floor_note"] in ("1층", "층 정보 없음") for i in results_of(o, "search_food")[-1]["items"][:3]),
                         f"{[(i['name'], i['floor_note']) for i in results_of(o, 'search_food')[-1]['items'][:3]]}" if results_of(o, "search_food") else "식당 도구 안 씀")},
    {"id": 13, "q": ["어르신 모시고 갈 만한 곳", "다른 곳은 없어?"],
     "expect": "두 번째 질문에서 앞서 보여준 장소를 빼고 새로 추천",
     "check": lambda o: (bool(top(o)) and bool(results_of(o, "recommend_places")[-1] and [a for n, a, _ in o["tool_results"] if n == "recommend_places"][-1].get("exclude")),
                         f"새 추천 {[r['place'] for r in top(o)]}" if top(o) else "추천 없음")},
]


def run_one(sc):
    history, known, last_place, shown, out = [], None, None, [], None
    for q in sc["q"]:
        history.append({"role": "user", "content": q})
        out = A.run(history, known, last_place, None, shown)
        for name, a, res in out["tool_results"]:
            if name == "recommend_places":
                known = a.get("user_type") or known
                last_place = res["results"][0]["place"]
                shown = list(dict.fromkeys(shown + [r["place"] for r in res["results"]]))
        history.append({"role": "assistant", "content": out["text"]})
    ok_cond, detail = sc["check"](out)
    ok_ground, bad = grounded(out)
    return {"id": sc["id"], "questions": sc["q"], "expect": sc["expect"],
            "tools": [t["tool"] for t in out["trace"]], "condition_ok": bool(ok_cond), "detail": detail,
            "grounded": ok_ground, "ungrounded_names": bad, "answer": out["text"]}


def main():
    rows = [run_one(sc) for sc in SCENARIOS]
    passed = sum(r["condition_ok"] and r["grounded"] for r in rows)
    docs = ROOT / "docs"
    (docs / "scenario_results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = [f"# 시나리오 테스트 결과", "",
             f"실행: {dt.datetime.now():%Y-%m-%d %H:%M} · 모델: {A.MODEL} · 통과 {passed}/{len(rows)}", "",
             "통과 = 조건 충족 + 답변의 장소·가게 이름이 모두 도구 결과에 있음(지어내지 않음).", "",
             "| # | 질문 | 기대 | 사용 도구 | 조건 | 근거 | 결과 |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['id']} | {' → '.join(r['questions'])} | {r['expect']} | {' → '.join(r['tools'])} | "
                     f"{'통과' if r['condition_ok'] else '실패'} | {'통과' if r['grounded'] else '실패: ' + ', '.join(r['ungrounded_names'])} | {r['detail']} |")
    lines += ["", "## 답변 원문", ""]
    for r in rows:
        lines += [f"**{r['id']}. {' → '.join(r['questions'])}**", "", r["answer"].strip(), ""]
    (docs / "시나리오_테스트.md").write_text("\n".join(lines), encoding="utf-8")
    for r in rows:
        print(r["id"], "조건", "O" if r["condition_ok"] else "X", "근거", "O" if r["grounded"] else "X", "|", " > ".join(r["tools"]), "|", r["detail"], r["ungrounded_names"] or "")
    print(f"통과 {passed}/{len(rows)}")


if __name__ == "__main__":
    main()
