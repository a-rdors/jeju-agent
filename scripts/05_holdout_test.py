"""확인용 시나리오 테스트: 튜닝에 쓰지 않은 새 질문으로 처음 보는 말에도 잘 되는지 본다.
채점 방식은 04_scenario_test.py와 같다(도구·조건·근거). 이 결과를 보고 코드를 고치면
이 세트도 '튜닝에 쓴 질문'이 되므로 결과 기록에 구분해 적는다.

실행: python scripts/05_holdout_test.py
결과: docs/시나리오_확인테스트.md, docs/holdout_results.json
"""
import datetime as dt
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
base = importlib.import_module("04_scenario_test")
results_of, top, run_one, A = base.results_of, base.top, base.run_one, base.A


def detail_place(o):
    r = results_of(o, "get_place_detail")
    return r[-1].get("place") if r else None


HOLDOUT = [
    {"id": "H1", "q": ["엄마가 보행기 쓰시는데 바닷가 산책할 만한 데 있을까"],
     "expect": "보행 불편 어르신으로 해석, 바다 장소",
     "check": lambda o: (bool(top(o)) and "바다" in top(o)[0]["themes"],
                         f"1순위 {top(o)[0]['place']} ({top(o)[0]['themes']})" if top(o) else f"추천 없음 / 도구 {[t['tool'] for t in o['trace']]}")},
    {"id": "H2", "q": ["애기 데리고 비 오는 날 갈 만한 곳"],
     "expect": "유모차 기준, 날씨 확인, 실내 장소",
     "check": lambda o: (bool(results_of(o, "get_weather")) and bool(top(o)) and "실내" in top(o)[0]["themes"],
                         f"날씨 {'O' if results_of(o, 'get_weather') else 'X'}, 1순위 {top(o)[0]['place'] if top(o) else '-'}")},
    {"id": "H3", "q": ["휠체어 타는 친구랑 제주시에서 구경할 만한 시장 있어?"],
     "expect": "제주시 안의 시장",
     "check": lambda o: (bool(top(o)) and "시장" in top(o)[0]["themes"] and top(o)[0]["where"].startswith("제주시"),
                         f"1순위 {top(o)[0]['place']} {top(o)[0]['where']}" if top(o) else "추천 없음")},
    {"id": "H4", "q": ["아버지가 휠체어 타시는데 함덕 근처 흑돼지 집 있어?"],
     "expect": "함덕 근처 흑돼지 식당(휠체어 확인 가게는 배지)",
     "check": lambda o: (bool(results_of(o, "search_food")) and bool(results_of(o, "search_food")[-1]["items"]),
                         f"{[(i['name'], i['wheelchair_entry']) for i in results_of(o, 'search_food')[-1]['items'][:3]]}" if results_of(o, "search_food") else "식당 도구 안 씀")},
    {"id": "H5", "q": ["할아버지가 오래 못 걸으셔서 잠깐 바람 쐬러 갈 곳"],
     "expect": "어르신 기준 짧은 코스(30분 안팎)",
     "check": lambda o: (bool(top(o)) and top(o)[0]["minutes"] <= 35,
                         f"1순위 {top(o)[0]['place']} 약 {top(o)[0]['minutes']}분" if top(o) else "추천 없음")},
    {"id": "H6", "q": ["전동휠체어로 사려니숲 갈 수 있어?"],
     "expect": "특정 장소 질문 → 사려니숲길 무장애나눔길 정보로 답",
     "check": lambda o: ("사려니" in (detail_place(o) or "") or any("사려니" in r["place"] for r in top(o)),
                         f"상세 {detail_place(o)}, 추천 {[r['place'] for r in top(o)]}")},
    {"id": "H7", "q": ["유모차로 서귀포에 있는 실내 전시 보러 가고 싶어"],
     "expect": "서귀포시 안의 실내 장소",
     "check": lambda o: (bool(top(o)) and "실내" in top(o)[0]["themes"] and top(o)[0]["where"].startswith("서귀포시"),
                         f"1순위 {top(o)[0]['place']} {top(o)[0]['where']}" if top(o) else "추천 없음")},
    {"id": "H8", "q": ["어르신 모시고 갈 곳 추천해 줘", "거기 화장실은 어디쯤 있어?"],
     "expect": "두 번째 질문에서 앞서 추천한 장소의 코스 상세 조회",
     "check": lambda o: (bool(results_of(o, "get_place_detail")),
                         f"상세 조회 장소 {detail_place(o)}")},
]


def main():
    rows = []
    for sc in HOLDOUT:
        try:
            rows.append(run_one(sc))
        except Exception as e:  # 시나리오 하나가 실패해도 나머지는 계속
            rows.append({"id": sc["id"], "questions": sc["q"], "expect": sc["expect"], "tools": [],
                         "condition_ok": False, "detail": f"오류: {type(e).__name__}: {e}", "grounded": False,
                         "ungrounded_names": [], "answer": ""})
    passed = sum(r["condition_ok"] and r["grounded"] for r in rows)
    docs = ROOT / "docs"
    (docs / "holdout_results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = ["# 확인용 시나리오 테스트 결과", "",
             f"실행: {dt.datetime.now():%Y-%m-%d %H:%M} · 모델: {A.MODEL} · 통과 {passed}/{len(rows)}", "",
             "튜닝에 쓰지 않은 새 질문. 통과 = 조건 충족 + 답변의 장소·가게 이름이 모두 도구 결과에 있음.", "",
             "| # | 질문 | 기대 | 사용 도구 | 조건 | 근거 | 결과 |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['id']} | {' → '.join(r['questions'])} | {r['expect']} | {' → '.join(r['tools'])} | "
                     f"{'통과' if r['condition_ok'] else '실패'} | {'통과' if r['grounded'] else '실패'} | {r['detail']} |")
    lines += ["", "## 답변 원문", ""]
    for r in rows:
        lines += [f"**{r['id']}. {' → '.join(r['questions'])}**", "", (r["answer"] or "").strip(), ""]
    (docs / "시나리오_확인테스트.md").write_text("\n".join(lines), encoding="utf-8")
    for r in rows:
        print(r["id"], "조건", "O" if r["condition_ok"] else "X", "근거", "O" if r["grounded"] else "X", "|",
              " > ".join(r["tools"]), "|", r["detail"], r.get("ungrounded_names") or "")
    print(f"통과 {passed}/{len(rows)}")


if __name__ == "__main__":
    main()
