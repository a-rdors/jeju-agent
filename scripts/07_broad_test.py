"""폭넓은 사용자 질문 테스트: 사용자가 실제로 입력할 만한 여러 경우를 한꺼번에 돌려 동작과 답변 형식을 점검한다.

질문 분류: 장소(이동 유형별) · 식당(식사 조건) · 병원·화장실 · 날씨 · 일정 · 여러 날 · 이어지는 질문 · 막연한 질문
         · 범위 밖 요청 · 줄임말·오타
자동 점검:
  1) 오류 없이 답했나
  2) 필요한 도구를 썼나(분류별 기대 도구)
  3) 답변 형식: 인사말·이모지·제목·목록 기호 없이, 분류별 고정 형식(굵은 이름으로 시작, '조심할 점:' 등)을 지켰나
  4) 근거: 답변의 장소·가게 이름이 모두 도구 결과에 있나
  5) 금지 표현: '안전해요', '맛집 1위' 등 단정·순위 표현이 없나

실행: python scripts/07_broad_test.py   (OPENAI_API_KEY 필요, 질문 수만큼 AI 호출 비용 발생)
결과: docs/폭넓은_질문_테스트.md, docs/broad_results.json
"""
import datetime as dt
import importlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
base = importlib.import_module("04_scenario_test")
A, grounded = base.A, base.grounded

EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
FORBIDDEN = re.compile(r"안전해요|안전합니다|맛집\s*\d|1위|최고의|무조건|100%")

# (분류, 질문들, 기대 도구 중 하나 이상, 형식 규칙)
CASES = [
    # --- 장소: 이동 유형별 ---
    ("장소", ["아빠가 휠체어 타시는데 바다 보러 갈 만한 데 있어?"], {"recommend_places"}, "place"),
    ("장소", ["전동휠체어로 숲길 산책할 데"], {"recommend_places"}, "place"),
    ("장소", ["유모차 끌고 서귀포에서 갈 만한 곳"], {"recommend_places"}, "place"),
    ("장소", ["돌 지난 아기랑 실내로 갈 곳 추천해줘"], {"recommend_places"}, "place"),
    ("장소", ["할머니가 무릎이 안 좋으신데 잠깐 바람 쐬러 갈 곳"], {"recommend_places"}, "place"),
    ("장소", ["부모님 모시고 제주시에서 박물관 가고 싶어"], {"recommend_places"}, "place"),
    ("장소", ["임신 8개월인데 무리 없이 갈 수 있는 곳"], {"recommend_places"}, "place"),
    ("장소", ["만삭 아내랑 바다 보고 싶어"], {"recommend_places"}, "place"),
    ("장소", ["휠체어 타는 동생이랑 중문 근처에서 갈 곳, 화장실 꼭 있어야 해"], {"recommend_places"}, "place"),
    ("장소", ["어르신 두 분 모시고 성산 쪽 가볍게 다녀올 데"], {"recommend_places"}, "place"),
    # --- 특정 장소 ---
    ("장소 확인", ["휠체어로 감귤박물관 갈 수 있어?"], {"get_place_detail", "recommend_places"}, "place"),
    ("장소 확인", ["유모차로 사려니숲 가능해?"], {"get_place_detail", "recommend_places"}, "place"),
    # --- 식당: 식사 조건 ---
    ("식당", ["할머니 이가 안 좋으신데 제주시에서 밥 먹을 곳"], {"search_food"}, "food"),
    ("식당", ["엄마가 속이 안 좋아서 순한 거 먹고 싶어. 서귀포"], {"search_food"}, "food"),
    ("식당", ["아이가 매운 걸 못 먹어. 애월에서 저녁 먹을 데"], {"search_food"}, "food"),
    ("식당", ["남편이 해산물 알레르기 있어. 성산 근처 식당"], {"search_food"}, "food"),
    ("식당", ["아버지 혈압 때문에 짜게 드시면 안 돼. 한림 쪽 식당"], {"search_food"}, "food"),
    ("식당", ["임산부인데 함덕에서 먹을 만한 곳"], {"search_food"}, "food"),
    ("식당", ["휠체어 타는 아빠랑 흑돼지 먹고 싶어. 서귀포 시내"], {"search_food"}, "food"),
    ("식당", ["유모차 들어갈 수 있는 카페 애월에"], {"search_food"}, "food"),
    ("식당", ["할아버지 모시고 중문에서 국수 먹을 데"], {"search_food"}, "food"),
    # --- 병원·화장실 ---
    ("의료", ["곽지해수욕장 근처 약국이랑 병원 어디야?"], {"find_nearby_help"}, "help"),
    ("의료", ["임신 중인데 감귤박물관 근처에 산부인과 있어?"], {"find_nearby_help"}, "help"),
    ("의료", ["동문시장 근처에 장애인 화장실 있어?"], {"find_nearby_help", "get_place_detail"}, "help"),
    # --- 날씨 ---
    ("날씨", ["내일 휠체어 타는 엄마랑 바다 가도 될까?"], {"get_weather", "recommend_places"}, "place"),
    ("날씨", ["주말에 비 온다던데 아기랑 갈 만한 데"], {"get_weather", "recommend_places"}, "place"),
    # --- 일정 ---
    ("일정", ["휠체어 아빠랑 서귀포에서 반나절 코스 짜줘"], {"plan_outing"}, "plan"),
    ("일정", ["어르신 모시고 애월에서 하루 일정 짜줘. 이가 안 좋으셔"], {"plan_outing"}, "plan"),
    ("일정", ["임산부랑 제주시에서 가볍게 동선 짜줘"], {"plan_outing"}, "plan"),
    ("여러 날", ["어르신 2명 모시고 서귀포로 1박 2일 가는데 일정 짜줘"], {"plan_outing"}, "plan"),
    ("여러 날", ["유모차랑 2박 3일 제주 일정 부탁해"], {"plan_outing"}, "plan"),
    # --- 이어지는 질문 ---
    ("이어서", ["휠체어로 갈 만한 데 추천해줘", "거기 화장실은 어디쯤 있어?"], {"get_place_detail"}, "any"),
    ("이어서", ["어르신 모시고 갈 만한 곳", "다른 곳은 없어?"], {"recommend_places"}, "place"),
    ("이어서", ["유모차로 갈 바다 추천", "그 근처 카페도 알려줘"], {"search_food"}, "food"),
    ("이어서", ["휠체어 타는 엄마랑 갈 실내", "거기 근처 약국은?"], {"find_nearby_help"}, "help"),
    ("이어서", ["아기랑 갈 만한 데", "거기 비 오면 어떡해?"], {"recommend_places", "get_weather", "get_place_detail"}, "any"),
    # --- 막연한 질문 ---
    ("막연", ["어디 갈 만한 데 있어?"], {"ask_user"}, "ask"),
    ("막연", ["추천해줘"], {"ask_user"}, "ask"),
    # --- 범위 밖 ---
    ("범위 밖", ["휠체어 타는 아빠랑 서울에서 갈 만한 곳"], set(), "scope"),
    ("범위 밖", ["어르신 모시고 묵을 숙소 추천해줘"], set(), "scope"),
    ("범위 밖", ["제주에서 제일 맛있는 집 1위 알려줘"], set(), "scope"),
    ("범위 밖", ["임신 중인데 감기약 먹어도 돼?"], set(), "scope"),
    ("범위 밖", ["식당 예약 좀 해줘"], set(), "scope"),
    # --- 줄임말·오타 ---
    ("줄임말", ["휠체어 바다 ㄱㄱ"], {"recommend_places"}, "place"),
    ("줄임말", ["할매랑 밥 어디서 먹지 제주시"], {"search_food"}, "food"),
    ("줄임말", ["유모차 카패 서귀포"], {"search_food"}, "food"),
]


def check_format(text, kind):
    lines = [l for l in text.strip().splitlines() if l.strip()]
    problems = []
    if EMOJI.search(text):
        problems.append("이모지")
    if any(l.lstrip().startswith(("#", "- ", "* ", "1.", "1)")) for l in lines):
        problems.append("제목·목록 기호")
    if re.match(r"\s*(안녕|좋아요|네[,!. ])", text):
        problems.append("인사말로 시작")
    if FORBIDDEN.search(text) and kind != "scope":  # 범위 밖 거절문은 '1위는 알려드릴 수 없어요'처럼 인용할 수 있음
        problems.append("금지 표현: " + FORBIDDEN.search(text).group(0))
    if kind == "place":
        if not lines or not lines[0].startswith("**"):
            problems.append("첫 줄이 '**장소** — 판정'이 아님")
        if "조심할 점" not in text:
            problems.append("'조심할 점:' 없음")
    elif kind == "food":
        if not lines or not lines[0].startswith("**"):
            problems.append("첫 줄이 '**가게** — 업종·층'이 아님")
        if "확인할 점" not in text:
            problems.append("'확인할 점:' 없음")
    elif kind == "help":
        if "119" not in text:
            problems.append("119 안내 없음")
    elif kind == "plan":
        if "→" not in lines[0] if lines else True:
            problems.append("첫 줄이 '**A → B**'가 아님")
        if "일정표" not in text and "+ 일정" not in text:
            problems.append("일정표 안내 없음")
    elif kind == "ask":
        if len(lines) > 2:
            problems.append("되묻기가 김")
    elif kind == "scope":
        if len(lines) > 4:
            problems.append("범위 밖 답변이 김")
    if kind in ("place", "food") and sum(1 for l in lines if l.startswith("**")) > (1 if kind == "place" else 3):
        problems.append("여러 곳을 나열함")
    if kind in ("place", "food", "help", "plan") and len(lines) > 12:
        problems.append(f"너무 김({len(lines)}줄)")
    return problems


def run_case(cat, qs, tools, kind):
    history, known, last_place, shown, out = [], None, None, [], None
    for q in qs:
        history.append({"role": "user", "content": q})
        out = A.run(history, known, last_place, None, shown)
        for name, a, res in out["tool_results"]:
            if name == "recommend_places" and res.get("results"):
                known = a.get("user_type") or known
                last_place = res["results"][0]["place"]
                shown = list(dict.fromkeys(shown + [r["place"] for r in res["results"]]))
        history.append({"role": "assistant", "content": out["text"]})
    used = {t["tool"] for t in out["trace"]}
    tool_ok = (not tools) or bool(used & tools)
    if kind == "scope":  # 범위 밖은 장소·가게를 추천하지 않아야 한다
        tool_ok = not any(t in used for t in ("recommend_places", "search_food", "plan_outing"))
    fmt = check_format(out["text"], kind) if kind != "any" else ([] if not EMOJI.search(out["text"]) else ["이모지"])
    ok_g, bad = grounded(out)
    return {"category": cat, "questions": qs, "expect_tools": sorted(tools), "used_tools": [t["tool"] for t in out["trace"]],
            "tool_ok": tool_ok, "format_problems": fmt, "grounded": ok_g, "ungrounded": bad, "answer": out["text"],
            "pass": tool_ok and not fmt and ok_g}


def main():
    rows = []
    for cat, qs, tools, kind in CASES:
        try:
            rows.append(run_case(cat, qs, tools, kind))
        except Exception as e:
            rows.append({"category": cat, "questions": qs, "expect_tools": sorted(tools), "used_tools": [], "tool_ok": False,
                         "format_problems": [f"오류: {type(e).__name__}: {e}"], "grounded": False, "ungrounded": [],
                         "answer": "", "pass": False})
        r = rows[-1]
        print(("OK " if r["pass"] else "XX ") + r["category"], "|", " → ".join(r["questions"])[:40], "|",
              ">".join(r["used_tools"]), "|", r["format_problems"] or "", r["ungrounded"] or "", flush=True)
    passed = sum(r["pass"] for r in rows)
    docs = ROOT / "docs"
    (docs / "broad_results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    by = {}
    for r in rows:
        by.setdefault(r["category"], [0, 0])
        by[r["category"]][0] += r["pass"]
        by[r["category"]][1] += 1
    lines = ["# 폭넓은 질문 테스트", "", f"실행: {dt.datetime.now():%Y-%m-%d %H:%M} · 모델: {A.MODEL} · 통과 {passed}/{len(rows)}", "",
             "점검: 오류 없음 · 필요한 도구 사용 · 답변 형식(분류별 고정 형식, 이모지·제목·목록 기호·인사말 없음) · "
             "근거(지어낸 장소·가게 없음) · 금지 표현 없음", "",
             "| 분류 | 통과 |", "|---|---|"] + [f"| {k} | {v[0]}/{v[1]} |" for k, v in by.items()] + \
            ["", "| 결과 | 분류 | 질문 | 사용 도구 | 문제 |", "|---|---|---|---|---|"]
    for r in rows:
        prob = "; ".join(r["format_problems"] + ([f"근거 없음: {', '.join(r['ungrounded'])}"] if r["ungrounded"] else [])
                         + ([] if r["tool_ok"] else ["필요한 도구 안 씀"]))
        lines.append(f"| {'통과' if r['pass'] else '실패'} | {r['category']} | {' → '.join(r['questions'])} | "
                     f"{' → '.join(r['used_tools'])} | {prob} |")
    lines += ["", "## 답변 원문", ""]
    for r in rows:
        lines += [f"**[{r['category']}] {' → '.join(r['questions'])}**", "", (r["answer"] or "").strip(), ""]
    (docs / "폭넓은_질문_테스트.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"통과 {passed}/{len(rows)}", by)


if __name__ == "__main__":
    main()
