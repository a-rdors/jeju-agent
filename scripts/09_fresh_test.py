"""새 질문 세트 테스트: 튜닝이 끝난 뒤 처음 만든 질문 10개로 한 번만 돌려 본다.

04(시나리오)·05(확인용)·07(폭넓은 질문)은 모두 튜닝 중에 보며 고쳤기 때문에 점수가 높게 나올 수 있다.
처음 실행한 결과를 이 세트의 공식 점수로 남긴다. 결과를 보고 고친 뒤 다시 돌릴 때는 TEST_OUT_DIR로
다른 곳에 저장해 첫 실행 기록을 덮어쓰지 않는다.
채점 방식은 04_scenario_test.py와 같다(조건 + 근거: 답변의 장소·가게 이름이 모두 도구 결과에 있나).

실행: python scripts/09_fresh_test.py   (OPENAI_API_KEY 필요, 질문당 AI 호출 비용 발생)
결과: docs/새질문_테스트.md, docs/fresh_results.json
"""
import datetime as dt
import importlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
base = importlib.import_module("04_scenario_test")
results_of, top, run_one, A, user_type_of = base.results_of, base.top, base.run_one, base.A, base.user_type_of


def detail_place(o):
    r = results_of(o, "get_place_detail")
    return r[-1].get("place") if r else None


def food(o):
    r = results_of(o, "search_food")
    return r[-1] if r else None


FRESH = [
    {"id": "F1", "q": ["다리 수술한 지 얼마 안 된 남편이랑 성산 쪽 바다 보러 가고 싶어"],
     "expect": "서귀포시 성산 근처 바다 장소",
     "check": lambda o: (bool(top(o)) and "바다" in top(o)[0]["themes"] and top(o)[0]["where"].startswith("서귀포시"),
                         f"이동 유형 {user_type_of(o)}, 1순위 {top(o)[0]['place']} {top(o)[0]['where']} ({top(o)[0]['themes']})" if top(o) else "추천 없음")},
    {"id": "F2", "q": ["유모차 끌고 제주시 쪽에서 반나절 다녀올 일정 짜줘"],
     "expect": "유모차 기준 일정(장소+식사 등 2곳 이상)",
     "check": lambda o: (bool(results_of(o, "plan_outing")) and len(results_of(o, "plan_outing")[-1]["stops"]) >= 2,
                         f"일정 {[s['name'] for s in results_of(o, 'plan_outing')[-1]['stops']]}" if results_of(o, "plan_outing") else "일정 도구 안 씀")},
    {"id": "F3", "q": ["전동휠체어 타는 동생이랑 한림에서 해산물 먹고 싶은데"],
     "expect": "한림 근처 해산물 식당",
     "check": lambda o: (food(o) is not None and bool(food(o)["items"]) and "한림" in str(food(o).get("around") or ""),
                         f"기준 {food(o).get('around')}, {[i['name'] for i in food(o)['items'][:3]]}" if food(o) else "식당 도구 안 씀")},
    {"id": "F4", "q": ["할머니 모시고 가는데 장애인 화장실 있는 실내 장소 알려줘"],
     "expect": "어르신 기준, 장애인 화장실 있는 실내 장소",
     "check": lambda o: (bool(top(o)) and top(o)[0]["accessible_toilet"] and "실내" in top(o)[0]["themes"],
                         f"1순위 {top(o)[0]['place']} 화장실 {top(o)[0]['accessible_toilet']} ({top(o)[0]['themes']})" if top(o) else "추천 없음")},
    {"id": "F5", "q": ["휠체어 타는데 오늘 비 오면 어디 가는 게 좋아?"],
     "expect": "오늘 날씨 확인, 실내 장소",
     "check": lambda o: (bool(results_of(o, "get_weather")) and bool(top(o)) and "실내" in top(o)[0]["themes"],
                         f"날씨 {'O' if results_of(o, 'get_weather') else 'X'}, 1순위 {top(o)[0]['place'] if top(o) else '-'}")},
    {"id": "F6", "q": ["천지연폭포 휠체어로 갈 수 있어?"],
     "expect": "특정 장소 질문 → 천지연폭포 정보로 답",
     "check": lambda o: ("천지연" in (detail_place(o) or "") or any("천지연" in r["place"] for r in top(o)),
                         f"상세 {detail_place(o)}, 추천 {[r['place'] for r in top(o)]}")},
    {"id": "F7", "q": ["유모차로 갈 만한 곳 추천해 줘", "거기 말고 다른 데는?"],
     "expect": "두 번째 질문에서 앞서 보여 준 곳을 빼고 새로 추천",
     "check": lambda o: (bool(top(o)) and not ({r["place"] for r in top(o)} & set(o["shown_before"])),
                         f"앞서 {o['shown_before']}, 새 추천 {[r['place'] for r in top(o)]}" if top(o) else "추천 없음")},
    {"id": "F8", "q": ["어머니가 휠체어 타시는데 갑자기 몸이 안 좋으셔. 서귀포 시내 쪽 응급실 어디야?"],
     "expect": "의료 찾기 도구로 응급실 안내",
     "check": lambda o: (bool(results_of(o, "find_nearby_help")) and "119" in o["text"],
                         f"의료 찾기 {'O' if results_of(o, 'find_nearby_help') else 'X'}, 119 안내 {'O' if '119' in o['text'] else 'X'}")},
    {"id": "F9", "q": ["제주시에서 휠체어로 갈 만한 곳 세 군데만 골라 줘"],
     "expect": "결과 3곳이 모두 제주시",
     "check": lambda o: (len(top(o)) >= 3 and all(r["where"].startswith("제주시") for r in top(o)),
                         ", ".join(f"{r['place']}({r['where']})" for r in top(o)) if top(o) else "추천 없음")},
    {"id": "F10", "q": ["아빠가 지팡이 짚으시는데 30분 안에 걸을 수 있는 숲길 있어?"],
     "expect": "어르신 기준, 걷는 시간이 기록된 30분 이하 숲 장소",
     "check": lambda o: (bool(top(o)) and "자연·숲" in top(o)[0]["themes"] and top(o)[0]["minutes"] is not None and top(o)[0]["minutes"] <= 30,
                         f"이동 유형 {user_type_of(o)}, 1순위 {top(o)[0]['place']} 약 {top(o)[0]['minutes']}분" if top(o) else "추천 없음")},
]


def main():
    rows = []
    for sc in FRESH:
        try:
            rows.append(run_one(sc))
        except Exception as e:  # 질문 하나가 실패해도 나머지는 계속
            rows.append({"id": sc["id"], "questions": sc["q"], "expect": sc["expect"], "tools": [],
                         "condition_ok": False, "detail": f"오류: {type(e).__name__}: {e}", "grounded": False,
                         "ungrounded_names": [], "answer": ""})
    passed = sum(r["condition_ok"] and r["grounded"] for r in rows)
    docs = Path(os.environ.get("TEST_OUT_DIR") or ROOT / "docs")
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "fresh_results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = ["# 새 질문 테스트 결과", "",
             f"실행: {dt.datetime.now():%Y-%m-%d %H:%M} · 모델: {A.MODEL} · 통과 {passed}/{len(rows)}", "",
             "튜닝이 끝난 뒤 처음 만든 질문. 첫 실행 결과를 그대로 적는다.",
             "통과 = 조건 충족 + 답변의 장소·가게 이름이 모두 도구 결과에 있음.", "",
             "| # | 질문 | 기대 | 사용 도구 | 조건 | 근거 | 결과 |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['id']} | {' → '.join(r['questions'])} | {r['expect']} | {' → '.join(r['tools'])} | "
                     f"{'통과' if r['condition_ok'] else '실패'} | {'통과' if r['grounded'] else '실패: ' + ', '.join(r['ungrounded_names'])} | {r['detail']} |")
    lines += ["", "## 답변 원문", ""]
    for r in rows:
        lines += [f"**{r['id']}. {' → '.join(r['questions'])}**", "", (r["answer"] or "").strip(), ""]
    (docs / "새질문_테스트.md").write_text("\n".join(lines), encoding="utf-8")
    for r in rows:
        print(r["id"], "조건", "O" if r["condition_ok"] else "X", "근거", "O" if r["grounded"] else "X", "|",
              " > ".join(r["tools"]), "|", r["detail"], r.get("ungrounded_names") or "")
    print(f"통과 {passed}/{len(rows)}")


if __name__ == "__main__":
    main()
