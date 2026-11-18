"""OpenAI 함수 호출로 도구를 고르고 실행하는 Agent 반복 구조.

흐름: 사용자 말 -> 모델이 도구 선택 -> 코드가 도구 실행 -> 결과를 모델에 다시 전달
      -> 충분하면 짧은 답변, 정보가 부족하면 ask_user로 버튼 질문.
"""
import json
import os
from pathlib import Path

from dotenv import load_dotenv

import tools as T

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
MAX_STEPS = 6

SYSTEM = """너는 '제주 같이나들이' 도우미야. 휠체어·유모차·어르신·임산부와 함께 제주 나들이를 준비하는 가족을 돕는다.

원칙
0. 너는 일반 여행 안내가 아니다. "어디 갈까"가 아니라 "이 가족이 거기 갈 수 있을까, 무엇을 조심해야 할까"에 답한다.
   접근성 근거(경사, 턱, 계단, 화장실, 주차, 쉼터)가 없는 추천은 하지 않는다.
1. 사용자가 가장 편해야 한다. 숫자(경사 몇 도, 몇 km)를 묻지 않는다. 일상어를 네가 해석한다.
2. ask_user는 이동 유형(누가 가는지)을 전혀 알 수 없을 때만 딱 한 번 쓴다.
   문장에 휠체어·전동·유모차·아기·할머니·부모님·어르신·무릎·임산부·임신 같은 단서가 있거나 '이미 확인된 이동 유형'이 있으면 절대 묻지 않는다.
   분위기·지역·동행인·날짜는 묻지 않는다. 모르면 조건 없이 바로 찾는다.
3. 장소를 추천하려면 반드시 recommend_places를 먼저 호출한다. 도구 결과에 없는 장소·시설·사실은 절대 말하지 않는다.
4. 답변은 아래 형식만 쓴다(자세한 내용은 화면 카드가 보여준다). 인사말·이모지·목록 기호·제목은 쓰지 않는다. 최대 4줄.
   [장소] 1순위 장소 하나만 쓴다(다른 후보는 화면의 '다른 곳 보기'에 있다).
          1순위는 recommend_places 결과의 첫 번째 장소다(화면 카드와 지도의 1번). 순서를 바꾸지 않는다.
          1줄: **장소 이름** — 판정(verdict 그대로)
          2줄: 이 가족에게 맞는 이유 한 문장
          3줄: 조심할 점: 한 문장 (watch_out·tips·확인 안 된 항목에서)
          4줄: 결과의 rain_alt가 있을 때만 "비 오면: rain_alt 이름". rain_alt가 없으면 이 줄을 쓰지 않는다(다른 추천 장소로 대신 채우지 않는다)
   [식당] 종류마다 1순위 가게 하나만 쓴다(나머지는 화면 카드에 있다). 라벨은 '조심할 점'이 아니라 반드시 '확인할 점:'.
          1줄: **가게 이름** — 업종 · 층(floor_note)
          2줄: 추천 이유(추정): why를 쉬운 말로
          3줄: 확인할 점: 전화로 물어볼 것 한 가지
          (식당을 두 종류 찾았으면 종류마다 이 3줄을 반복한다)
   [병원·약국·화장실] 약국·병원·산부인과·응급실·화장실을 물으면 find_nearby_help를 쓰고 이 형식으로 답한다.
          1줄: 가장 가까운 곳들 이름과 거리
          2줄: 응급 상황에는 119에 먼저 연락하세요.
   [일정] plan_outing을 썼으면 장소 형식이 아니라 반드시 이 형식.
          1줄: **A → B → C**
          2줄: 각 곳을 고른 이유를 한 문장으로
          3줄: 일정표를 내려받을 수 있어요.
   [되묻기] ask_user만 쓰고 글은 질문 한 줄.
   [범위 밖] 제주 밖 지역, 숙소 추천, 맛 평가·순위, 의학적 판단, 예약 대행: 1줄로 못 하는 이유, 1줄로 대신 할 수 있는 것.
          범위 밖 요청에는 도구를 부르지 않고 장소·가게를 추천하지 않는다.
   해산물 알레르기(no_seafood)일 때는 food_kind에 '해산물'을 넣지 않는다.
5. 쉬운 말을 쓴다. "기준 초과" 같은 말 대신 "가파른 구간이 있어요"처럼 말한다.
6. 확인되지 않은 정보는 "확인이 안 돼요, 가기 전에 전화해 보세요"라고 말한다. 안전을 보장하는 말("안전해요")은 하지 않는다.
10. '다른 곳', '또 없어?'라고 하면 '이미 보여준 장소'를 exclude에 넣어 다시 recommend_places를 부른다.
7. '거기', '그곳', '그 근처'는 '직전 추천 장소'를 뜻한다. 다시 묻지 말고 그 장소 이름으로 도구를 부른다.
   사용자가 특정 장소의 길·화장실·쉼터를 물으면 get_place_detail, 약국·병원·응급은 find_nearby_help를 쓴다.
   버스로 가는 법을 물으면 get_place_detail의 bus_stops(가까운 정류소 이름·직선거리)를 전한다. 저상버스·노선 여부는 확인이 안 된다고 말한다.
8. 식당·카페는 search_food를 쓴다. 제주 전체 식당이 대상이다(휠체어 진입은 배지일 뿐 필터가 아니다).
   휠체어 이용자 가족이면 prefer_wheelchair=true. wheelchair_only는 "휠체어로 들어갈 수 있는 곳만"이라고 할 때만.
   식사 조건(diet_needs, 여러 개 가능): 이가 안 좋다·씹기 힘들다·틀니 → soft / 소화·속·위장이 안 좋다 → gentle /
   매운 걸 못 먹는다 → mild / 해산물 알레르기 → no_seafood / 혈압·짜게 먹으면 안 된다 → low_salt / 아이·애기와 식사 → kids /
   임산부·임신 중 → no_raw(날음식·술 피하기, 사용자가 원하지 않는다고 하면 빼기).
   어떤 장소나 가게 '근처'를 물으면 place에 그 이름을 그대로 넣는다(식당 이름도 된다). 동네를 말하면 area.
   결과에 anchor_not_found가 있으면 위치를 못 찾았다고 솔직히 말하고 동네 이름을 물어본다.
   맛 평가·순위·의학적 조언은 하지 않는다. why(업종·가게 이름으로 추정한 근거)를 쉬운 말로 전하고,
   메뉴와 건강 상태에 맞는지는 call_questions로 가게에 전화해 확인하라고 안내한다.

9. 날짜나 날씨를 말하면 시스템이 미리 날씨를 조회해 '참고 날씨'로 준다. 그 내용으로 판단한다.
   비 예보면 실내 장소를 함께 제안하고, 주의사항(tips)은 쉬운 말로 전달한다. 날씨 자체를 길게 설명하지 않는다.

11. 사용자가 일정·코스·반나절·하루·동선·묶어 달라고 할 때만 plan_outing을 쓴다. 단순히 장소나 식당 하나를 물으면 쓰지 않고,
    일정 이야기도 꺼내지 않는다. plan_outing 결과는 들르는 순서와 이유를 짧게 말하고 "일정표를 내려받을 수 있어요"라고 안내한다.
    1박 2일·2박 3일처럼 여러 날 일정이나 시간표를 원해도 날짜별 시간표를 지어내지 않는다. 첫 나들이를 plan_outing으로 제안하고
    "다른 날 갈 곳은 결과 카드의 '+ 일정'으로 담아 일정표에 모을 수 있어요"라고 안내한다.
    "전체 동선을 짜 드릴게요", "2일차는…"처럼 여러 날 일정을 만들어 주겠다는 제안도 하지 않는다.
13. 사용자가 휠체어·장애를 말하지 않았으면 '장애인'이라는 말을 쓰지 않는다(화장실은 '넓은 화장실', 주차는 '주차장').
12. 도구 결과에 없는 현장 상황(모래길, 혼잡, 공사 등)을 추측해서 말하지 않는다. 주의할 점은 결과의 watch_out, tips, checks에 있는 것만 말한다.
    장소에 rain_alt(비 오면 대신 갈 실내 장소)가 있으면 한 줄로 알려준다.

이동 유형 해석: '휠체어'라고만 하면 종류를 묻지 말고 manual_wheelchair로 정한다(수동이 경사에 더 조심스러운 기준).
'전동' -> electric_wheelchair, '유모차/아기' -> stroller, '부모님/할머니/어르신/무릎' -> senior, '임산부/임신/만삭' -> pregnant.
theme은 사용자가 분위기(바다, 마을, 숲, 꽃, 역사, 시장 등)를 직접 말했을 때만 넣는다. 비·실내·박물관·미술관 -> 실내. '산책'만으로는 theme을 넣지 않는다.
'잠깐/가볍게' -> max_minutes 30, '반나절' -> 제한 없음. 화장실을 언급하면 need_toilet true."""

TOOL_SPECS = [
    {"type": "function", "function": {
        "name": "recommend_places",
        "description": "이동 유형·동네·분위기·화장실 필요 여부로 무장애 나들이 장소를 추천 순서대로 찾는다.",
        "parameters": {"type": "object", "properties": {
            "user_type": {"type": "string", "enum": list(T.USER_TYPES.keys())},
            "area": {"type": "string", "description": "사용자가 말한 동네·지역(예: 애월, 협재, 서귀포). 없으면 생략"},
            "theme": {"type": "string", "enum": ["바다", "마을", "자연·숲", "역사·문화", "실내", "시장"]},
            "need_toilet": {"type": "boolean"},
            "max_minutes": {"type": "integer"},
            "limit": {"type": "integer"},
            "exclude": {"type": "array", "items": {"type": "string"}, "description": "이미 보여준 장소(다른 곳을 원할 때)"}},
            "required": ["user_type"]}}},
    {"type": "function", "function": {
        "name": "get_place_detail",
        "description": "장소의 코스 흐름: 출발점부터 주의 지점, 쉼터, 장애인 화장실 위치를 순서대로. 출발점에서 가까운 버스 정류소(bus_stops)도 준다.",
        "parameters": {"type": "object", "properties": {
            "place": {"type": "string"}, "user_type": {"type": "string", "enum": list(T.USER_TYPES.keys())}},
            "required": ["place"]}}},
    {"type": "function", "function": {
        "name": "find_nearby_help",
        "description": "장소(또는 현재 위치)에서 가장 가까운 약국·병의원·응급실. 물어본 종류만 kinds에 넣는다(약국만 물으면 ['약국']). 약국은 폐업 기록이 있는 곳을 뺐다.",
        "parameters": {"type": "object", "properties": {
            "place": {"type": "string"},
            "kinds": {"type": "array", "items": {"type": "string", "enum": ["약국", "병·의원", "응급실"]}}}}}},
    {"type": "function", "function": {
        "name": "search_food",
        "description": "제주 식당·카페 찾기(약 1만 9천 곳). 식사 조건으로 고르고 휠체어 진입 확인 가게는 배지로 표시.",
        "parameters": {"type": "object", "properties": {
            "food_kind": {"type": "string", "enum": list(T.FOOD_KINDS.keys())},
            "diet_needs": {"type": "array", "items": {"type": "string", "enum": list(T.DIET_NEEDS.keys())}},
            "prefer_wheelchair": {"type": "boolean"},
            "avoid_upstairs": {"type": "boolean", "description": "거동이 불편하면 true(1층 가게 우선)"},
            "area": {"type": "string", "description": "동네·지역(예: 성산, 애월, 서귀포)"},
            "place": {"type": "string", "description": "근처의 기준이 되는 이름. 추천했던 나들이 장소나 식당·카페 이름(예: 서귀포흑돈)"},
            "wheelchair_only": {"type": "boolean"},
            "limit": {"type": "integer"}}}}},
    {"type": "function", "function": {
        "name": "get_weather",
        "description": "장소나 동네의 날씨 예보(7일 이내)와 접근성 주의사항(비·미끄러운 길·강풍).",
        "parameters": {"type": "object", "properties": {
            "place": {"type": "string"}, "area": {"type": "string"},
            "when": {"type": "string", "description": "오늘, 내일, 모레, 주말, 토요일, 또는 YYYY-MM-DD"}}}}},
    {"type": "function", "function": {
        "name": "plan_outing",
        "description": "반나절 나들이 일정(장소 1곳 → 근처 식당 1곳 → 원하면 카페). 사용자가 일정·코스·반나절·하루·동선을 원할 때만.",
        "parameters": {"type": "object", "properties": {
            "user_type": {"type": "string", "enum": list(T.USER_TYPES.keys())},
            "area": {"type": "string"}, "theme": {"type": "string", "enum": ["바다", "마을", "자연·숲", "역사·문화", "실내", "시장"]},
            "diet_needs": {"type": "array", "items": {"type": "string", "enum": list(T.DIET_NEEDS.keys())}},
            "with_cafe": {"type": "boolean"}, "need_toilet": {"type": "boolean"}},
            "required": ["user_type"]}}},
    {"type": "function", "function": {
        "name": "ask_user",
        "description": "꼭 필요한 정보가 없을 때 사용자에게 버튼으로 답할 수 있는 질문을 한다.",
        "parameters": {"type": "object", "properties": {
            "question": {"type": "string"},
            "options": {"type": "array", "items": {"type": "string"}, "maxItems": 5}},
            "required": ["question", "options"]}}},
]

TOOL_FUNCS = {
    "recommend_places": T.recommend_places,
    "get_place_detail": T.get_place_detail,
    "find_nearby_help": T.find_nearby_help,
    "search_food": T.search_food,
    "get_weather": T.get_weather,
    "plan_outing": T.plan_outing,
}


def _llm_view(name, result):
    """모델에게는 필요한 만큼만 전달한다(전체 지점 목록·판정 근거 원문은 화면에서만 사용)."""
    if not isinstance(result, dict):
        return json.dumps(result, ensure_ascii=False, default=str)
    if name == "get_place_detail":
        result = {k: v for k, v in result.items() if k not in ("all_points", "evidence")}
    if name == "recommend_places" and isinstance(result.get("results"), list):
        result = {**result, "results": [{k: v for k, v in x.items() if k != "evidence"} for x in result["results"]]}
    return json.dumps(result, ensure_ascii=False, default=str)


def available():
    return bool(os.getenv("OPENAI_API_KEY"))


WEATHER_WORDS = r"오늘|내일|모레|주말|토요일|일요일|[월화수목금]요일|비가|비 오|비오|날씨|바람"


def plan_text(plan, multi_day=False):
    """일정 답변은 코드가 직접 만든다(형식이 항상 같도록)."""
    stops = plan.get("stops") or []
    if not stops:
        return "조건에 맞는 일정을 만들지 못했어요. 동네나 분위기를 바꿔 다시 말씀해 주세요."
    lines = ["**" + " → ".join(st["name"] for st in stops) + "**"]
    reasons = []
    for st in stops:
        if st["kind"] == "place":
            reasons.append(f"{st['name']}: {st['verdict']}")
        else:
            why = " · ".join(w.split(": ", 1)[-1] for w in st.get("why", []))
            fl = st.get("floor_note", "")
            reasons.append(f"{st['name']}: {st.get('food_type', '')}" + (f" · {fl}" if fl else "") + (f" · {why}" if why else ""))
    lines.append(" / ".join(reasons))
    alt = next((st["rain_alt"] for st in stops if st.get("rain_alt")), None)
    if alt:
        lines.append(f"비 오면: {alt['name']}")
    lines.append("일정표를 내려받을 수 있어요.")
    if multi_day:
        lines.append("다른 날 갈 곳은 결과 카드의 + 일정으로 담아 일정표에 모을 수 있어요.")
    return "\n".join(lines)


THEME_HINTS = [("바다", r"바다|해변|해안|바닷가|해수욕"), ("시장", r"시장"),
               ("자연·숲", r"(?<![가-힣])산(?!책)|산을|산이|오름|숲|풍경|경치|자연|꽃|단풍|억새"),
               ("실내", r"실내|박물관|미술관|전시"), ("역사·문화", r"역사|유적|문화"), ("마을", r"마을|골목")]


def theme_from(text):
    """질문 속 분위기 말 → 테마(모델이 빠뜨렸을 때 코드가 채운다)"""
    import re
    return next((k for k, p in THEME_HINTS if re.search(p, text or "")), None)


def normalize_answer(text, tool_results, last_q="", user_type=None):
    """AI 답변의 형식을 코드로 한 번 더 맞춘다.
    - 일정을 짰으면 일정 형식으로 다시 만든다
    - 장소·식당 답변의 '다만 …' 줄은 '조심할 점:'으로 통일한다
    - 병원·약국·화장실 결과가 있으면 119 안내로 끝낸다"""
    import re
    plans = [res for name, _, res in tool_results if name == "plan_outing"]
    if plans and plans[-1].get("stops"):
        multi = bool(re.search(r"\d\s*박|박\s*\d\s*일|며칠|여러\s*날|일차", last_q))
        return plan_text(plans[-1], multi)
    lines = text.splitlines()
    out = []
    for ln in lines:
        stripped = ln.strip()
        if re.match(r"^(다만|단,|단 |주의할 점:|유의할 점:)", stripped):
            ln = "조심할 점: " + re.sub(r"^(다만|단,|단|주의할 점:|유의할 점:)\s*", "", stripped)
        out.append(ln)
    text = "\n".join(out)
    names = {name for name, _, _ in tool_results}
    if "search_food" in names and "recommend_places" not in names:  # 식당 답변은 '확인할 점'으로 통일
        text = text.replace("조심할 점:", "확인할 점:")
        fixed = []
        for ln in text.splitlines():  # '확인이 안 돼요 …' 같은 줄도 '확인할 점:'으로
            if "확인할 점" not in text and re.match(r"^\s*확인이 안 돼", ln):
                ln = "확인할 점: " + re.sub(r"^\s*확인이 안 돼요?[,.]?\s*(가기 전에 전화해 보세요[:.]?)?\s*", "", ln)
            fixed.append(ln)
        text = "\n".join(fixed)
        if "확인할 점" not in text:
            f = [res for name, _, res in tool_results if name == "search_food"][-1]
            qs = f.get("call_questions") or ["입구에 턱이나 계단이 있나요?"]
            text = text.rstrip() + f"\n확인할 점: 전화로 \"{qs[0]}\"라고 물어보세요."
    detail_only = "get_place_detail" in names and "recommend_places" not in names and "search_food" not in names
    if ("recommend_places" in names or detail_only) and "조심할 점" not in text:
        if "recommend_places" in names:
            rec = [res for name, _, res in tool_results if name == "recommend_places"][-1]
            top = (rec.get("results") or [{}])[0]
        else:  # 특정 장소 확인(get_place_detail)도 같은 형식으로 조심할 점을 붙인다
            top = [res for name, _, res in tool_results if name == "get_place_detail"][-1] or {}
        miss = [c["item"] for c in top.get("checks", []) if isinstance(c, dict) and not c.get("known")]
        watch = top.get("watch_out") or top.get("tips") or [None]
        note = (watch[0] if isinstance(watch, list) else watch) or (
            f"{T.josa(T.join_and(miss[:2]), '은는')} 확인이 안 돼요. 가기 전에 전화해 보세요." if miss else "현장 상황은 가기 전에 한 번 확인해 보세요.")
        body = text.rstrip().splitlines()
        insert_at = next((i for i, l in enumerate(body) if l.startswith("비 오면")), len(body))
        body.insert(insert_at, "조심할 점: " + note)
        text = "\n".join(body)
    content_tools = [n for n in names if n not in ("get_weather", "ask_user")]
    if content_tools and set(content_tools) == {"find_nearby_help"}:
        built = help_text(tool_results, last_q)
        if built:
            return built
    if any(name == "find_nearby_help" for name, _, _ in tool_results) and "119" not in text:
        text = text.rstrip() + "\n응급 상황에는 119에 먼저 연락하세요."
    return text


def help_text(tool_results, last_q=""):
    """병원·약국·화장실 답변은 코드가 직접 만든다(항상 같은 형식)."""
    import re
    calls = [(a, r) for n, a, r in tool_results if n == "find_nearby_help" and isinstance(r, dict) and r.get("help")]
    if not calls:
        return None
    args, res = calls[-1]
    base = "현재 위치" if res.get("place") == "현재 위치" else res.get("place", "")
    wc_kind = "기저귀 교환대" if re.search(r"기저귀", last_q) else ("장애인 화장실" if re.search(r"화장실", last_q) else None)
    if wc_kind and res["help"].get(wc_kind):
        # 화장실을 물었으면 병원·약국이 아니라 가장 가까운 화장실로 답한다
        t = res["help"][wc_kind][0]
        dist = f" · {t['km']}km" if t.get("km") is not None else ""
        what = "기저귀 교환대가 있는 공중화장실" if wc_kind == "기저귀 교환대" else "장애인 칸이 있는 공중화장실"
        lines = [f"**{t['name']}** — 공중화장실{dist}",
                 f"{base}에서 가장 가까운 {what}이에요." + (f" 장애인 칸 {t['accessible_count']}개." if t.get("accessible_count") else ""),
                 "확인할 점: 여는 시간은 가기 전에 관리기관에 전화로 확인해 보세요.",
                 "응급 상황에는 119에 먼저 연락하세요."]
        return "\n".join(lines)
    order = [k for k in (args.get("kinds") or ["약국", "병·의원", "응급실"]) if res["help"].get(k)]
    if not order:
        return None
    kind = order[0]
    top = res["help"][kind][0]
    kind_is = kind + ("이에요." if T.josa(kind, "은는").endswith("은") else "예요.")
    base = "현재 위치" if res.get("place") == "현재 위치" else res.get("place", "")
    dist = f" · {top['km']}km" if top.get("km") is not None else ""
    lines = [f"**{top['name']}** — {kind}{dist}"]
    if top.get("km") is not None:
        lines.append(f"{base}에서 가장 가까운 {kind_is}" + (" 영업 중으로 확인됐어요." if top.get("status") else ""))
    else:
        lines.append(f"{base}에 있는 {kind_is}")
    if kind == "응급실":
        lines.append("확인할 점: 가기 전에 전화로 지금 진료가 되는지 물어보세요.")
    else:
        lines.append("확인할 점: 가기 전에 전화로 문을 열었는지 확인해 보세요.")
    lines.append("응급 상황에는 119에 먼저 연락하세요.")
    return "\n".join(lines)


def help_kinds(text):
    """질문에서 찾는 종류: '약국' → ['약국'], '응급실' → ['응급실'], '병원' → ['병·의원', '응급실']. 없으면 None."""
    import re
    kinds = []
    if re.search(r"약국|약\s*사|약\s*살|해열제|파스|밴드", text):
        kinds.append("약국")
    if re.search(r"병원|의원|진료|다쳤|다치|아파|열이", text):
        kinds += ["병·의원", "응급실"]
    elif re.search(r"응급", text):
        kinds.append("응급실")
    return list(dict.fromkeys(kinds)) or None


def detect_user_type(history):
    """대화에 이동 유형 단서가 있으면 코드로 먼저 정한다(불필요한 되묻기 방지)."""
    import re
    text = " ".join(m["content"] for m in history if m["role"] == "user")
    return next((k for k, p in TYPE_WORDS if re.search(p, text)), None)


def run(history, known_user_type=None, last_place=None, user_location=None, shown_places=None):
    """user_location: (위도, 경도). 화면(지도)에서 위치 권한을 허용하면 넘겨받는다."""
    """history: [{"role": "user"/"assistant", "content": str}, ...]
    반환: {"text": 답변, "ask": {question, options} 또는 None, "tool_results": [(이름, 인자, 결과)], "trace": [...]}"""
    from openai import OpenAI

    client = OpenAI()
    import re
    system = SYSTEM
    known_user_type = known_user_type or detect_user_type(history)
    if known_user_type:
        system += f"\n\n이미 확인된 이동 유형: {known_user_type}. 다시 묻지 말고 이 값을 쓴다."
    if last_place:
        system += f"\n직전 추천 장소: {last_place}"
    if shown_places:
        system += "\n이미 보여준 장소: " + ", ".join(shown_places)
    tool_results, trace = [], []
    last_q = next((m["content"] for m in reversed(history) if m["role"] == "user"), "")
    food_q = re.search(r"식당|맛집|밥|카페|먹|음식|해산물|흑돼지|국수", last_q)
    vague = re.fullmatch(r"\s*(어디|뭐|추천|갈\s*만한|놀러|가볼|좋은)[^가-힣]*.{0,15}", last_q) is not None
    if not known_user_type and not food_q and not last_place and vague:
        # 단서가 전혀 없는 짧은 질문이면 AI에 맡기지 않고 버튼으로 바로 묻는다(항상 같은 동작)
        ask = {"question": "누구와 함께 가시나요?", "options": ["휠체어", "전동 휠체어", "유모차", "어르신", "임산부"]}
        return {"text": ask["question"], "ask": ask, "tool_results": [], "trace": [{"tool": "ask_user", "args": ask}]}
    named = T.match_place(next((w for w in re.findall(r"[가-힣]{3,}", last_q) if T.match_place(w)), None))
    if named:
        system += f"\n사용자가 말한 장소: {named}. 이 장소에 갈 수 있는지 물으면 get_place_detail(place='{named}')로 확인한다."

    # 질문 속 가게·장소 이름을 동네 이름보다 먼저 찾는다('서귀포흑돈으로' → 가게 '서귀포흑돈', 동네 '서귀포' 아님)
    tokens = [re.sub(r"(으로|에서|에는|에|로|이랑|랑|하고|까지|부터|근처|쪽|은|는|을|를|도)$", "", w)
              for w in re.findall(r"[가-힣A-Za-z0-9]+", last_q)]
    said_place = None
    lm = T.find_landmark(last_q)
    if lm:
        said_place = lm[2]  # '공항 근처' → 제주공항 기준(가게 이름 '…제주공항'으로 잘못 잡지 않게)
    for tok in ([] if lm else tokens):
        if len(tok) < 3:
            continue
        a = T.match_place(tok) or (lambda r: r[2] if r and re.sub(r"\s", "", r[2]) == tok else None)(T.resolve_anchor(tok))
        if a:
            said_place = a
            break
    if (re.search(r"화장실|기저귀|약국|병원|응급", last_q) and not re.search(r"코스|길|경사|산책|거기|그곳|그 안|안에|어디쯤", last_q)):
        system += "\n이번 질문은 근처 화장실·약국·병원 질문이다. get_place_detail이 아니라 find_nearby_help를 쓴다."
    if food_q and not re.search(r"구경|산책|바다\s*보|관광|가\s*볼|놀러|가볼", last_q):
        system += "\n이번 질문은 식당·카페 질문이다. recommend_places가 아니라 search_food를 쓴다."
    outside = re.search(r"서울|부산|경기|인천|대구|대전|광주|울산|세종|강원|충청|전라|경상|전주|여수|경주|강릉|속초", last_q)
    if outside and not re.search(r"제주|서귀포", last_q):
        # 제주 밖 지역: AI에 맡기지 않고 항상 같은 답(제주 장소를 엉뚱하게 추천하지 않게)
        return {"text": "제주 지역만 안내할 수 있어요.\n제주로 오시면 함께 가실 분에 맞춰 갈 만한 곳과 식당을 찾아드릴게요.",
                "ask": None, "tool_results": [], "trace": []}
    taste_rank = re.search(r"제일\s*맛있|가장\s*맛있|최고\s*맛집|맛집\s*(순위|랭킹)|1\s*위|순위|랭킹|베스트\s*\d", last_q)
    if taste_rank and re.search(r"맛|식당|집|가게|음식|카페", last_q):
        # 맛 평가·순위: 근거 데이터가 없으므로 AI에 맡기지 않고 항상 같은 답
        return {"text": "범위 밖 요청이에요. 맛 평가나 순위는 근거 자료가 없어서 알려드릴 수 없어요.\n"
                        "대신 함께 가실 분과 동네를 말씀해 주시면 들어가기 편한 식당을 찾아드릴게요.",
                "ask": None, "tool_results": [], "trace": []}
    if re.search(r"\d\s*박|박\s*\d\s*일|며칠|여러\s*날|일차|일정\s*표", last_q):
        # 여러 날 요청: 날짜별 시간표를 만들지 않는다는 결정을 이번 답변에 강하게 적용
        system += ("\n이번 질문은 여러 날 일정 요청이다. 첫 나들이 하나만 plan_outing으로 제안한다. "
                   "여러 날·날짜별 일정표를 정리해 주겠다는 제안('정리해 드릴게요', '짜 드릴게요')을 절대 하지 않는다. "
                   "답변 마지막 문장은 반드시 '다른 날 갈 곳은 결과 카드의 + 일정으로 담아 일정표에 모을 수 있어요.'로 끝낸다.")
    if said_place:
        system += f"\n사용자가 말한 가게·장소: {said_place}. 그 근처를 물으면 place='{said_place}'로 찾는다."
    said_area = next((w for w in tokens if w and (not said_place or w not in said_place) and T.find_area(w)), None)
    if re.search(WEATHER_WORDS, last_q):  # 날짜·날씨 질문이면 코드가 먼저 날씨를 확인한다
        when = next((w for w in ("내일", "모레", "주말", "토요일", "일요일") if w in last_q), "오늘")
        area = next((w for w in re.findall(r"[가-힣]{2,4}", last_q)
                     if (T.find_area(w) or {}).get("lat") is not None), None)
        if last_place and re.search(r"거기|그곳|그 근처", last_q):
            wx_args = {"place": last_place, "when": when}
        else:
            wx_args = {"area": area, "when": when}
        wx = T.get_weather(**wx_args)
        tool_results.append(("get_weather", wx_args, wx))
        trace.append({"tool": "get_weather", "args": wx_args})
        system += "\n참고 날씨: " + _llm_view("get_weather", wx)
        if re.search(r"가도|갈\s*만|갈\s*곳|가볼|바다|산책|구경|나들이|어디", last_q):
            # 날씨와 갈 곳을 함께 물으면 날씨만 답하고 끝내지 않게
            system += "\n이번 질문은 날씨와 갈 곳을 함께 묻는다. 날씨는 이미 확인했으니 다시 부르지 말고 반드시 recommend_places를 불러 장소 형식으로 답한다."
    messages = [{"role": "system", "content": system}] + history
    for _ in range(MAX_STEPS):
        resp = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOL_SPECS)
        msg = resp.choices[0].message
        if not msg.tool_calls:
            text = normalize_answer(msg.content or "", tool_results, last_q)
            if not re.search(r"장애|휠체어", last_q):  # 사용자가 직접 '장애인'이라고 말했으면 그대로 둔다
                text = T.neutral_words(text, known_user_type)  # 휠체어를 말하지 않았으면 '장애인' 대신 일상어
            return {"text": text, "ask": None, "tool_results": tool_results, "trace": trace}
        messages.append({"role": "assistant", "content": msg.content or "",
                         "tool_calls": [c.model_dump() for c in msg.tool_calls]})
        for call in msg.tool_calls:
            name = call.function.name
            try:
                args = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            trace.append({"tool": name, "args": args})
            if name == "ask_user":
                return {"text": args.get("question", ""), "ask": args, "tool_results": tool_results, "trace": trace}
            if name == "recommend_places" and shown_places and re.search(r"다른|또|말고|새로운", last_q) and not args.get("exclude"):
                args["exclude"] = list(shown_places)  # '다른 곳' 요청인데 모델이 제외 목록을 빠뜨린 경우
            if (name == "search_food" and said_place and not args.get("place")
                    and (not args.get("area") or said_place.startswith(str(args.get("area"))))):
                args["place"] = said_place  # '서귀포흑돈 근처'를 '서귀포 전체'로 잘못 찾지 않게
                args.pop("area", None)
            if name == "get_weather" and args.get("place"):
                # 사용자가 말했거나 도구 결과에 나온 장소만 쓴다. 모델이 스스로 고른 장소(예: 아무 해안길)는 빼고
                # 동네 날씨로 본다(그 장소를 답에 지어내 추천하지 않게)
                known = {last_place, said_place, named, *(shown_places or [])}
                for _, _, res in tool_results:
                    if isinstance(res, dict):
                        known.add(res.get("place"))
                        known |= {x.get("place") for x in res.get("results", []) if isinstance(x, dict)}
                if args["place"] not in known:
                    args.pop("place")
                    args.setdefault("area", said_area)
            if name == "find_nearby_help" and known_user_type and "user_type" not in args:
                args["user_type"] = known_user_type  # 임산부면 산부인과도 함께
            if name == "find_nearby_help":
                asked = help_kinds(last_q)
                if asked:
                    args["kinds"] = asked  # 약국만 물으면 약국만(병원까지 섞지 않게)
                near_me = re.search(r"내\s*위치|여기|지금\s*있는|현재\s*위치|근처|가까운", last_q)
                vague_place = not args.get("place") or T.resolve_anchor(args.get("place")) is None
                if user_location and (vague_place or (near_me and not said_place and not said_area)):
                    args["origin_lat"], args["origin_lon"] = user_location
                    args.pop("place", None)
            if name == "search_food":
                args["limit"] = max(3, int(args.get("limit") or 5))  # 화면 카드가 비지 않게 최소 3곳
                if known_user_type in ("manual_wheelchair", "electric_wheelchair") and "prefer_wheelchair" not in args:
                    args["prefer_wheelchair"] = True
            if name == "search_food" and known_user_type in T.MOBILITY_TYPES and "avoid_upstairs" not in args:
                args["avoid_upstairs"] = True  # 휠체어·유모차·어르신이면 1층 가게를 앞으로
            if name in ("recommend_places", "plan_outing") and not args.get("theme") and theme_from(last_q):
                args["theme"] = theme_from(last_q)  # '산을 좋아해요' → 자연·숲 (모델이 분위기를 빠뜨린 경우)
            if name in ("recommend_places", "search_food", "plan_outing") and said_area and not args.get("area") and not args.get("place"):
                args["area"] = said_area  # 사용자가 말한 동네를 모델이 빠뜨린 경우 코드가 채운다
            if (name in ("recommend_places", "search_food", "plan_outing") and user_location and not said_area
                    and not args.get("area") and not args.get("place")):
                # 동네를 말하지 않았고 현재 위치가 있으면 '내 근처' 기준으로 찾는다
                args["origin_lat"], args["origin_lon"] = user_location
            try:
                result = TOOL_FUNCS[name](**args)
            except Exception as e:  # 도구 오류도 모델에 알려 다시 판단하게 한다
                result = {"error": f"{type(e).__name__}: {e}"}
            tool_results.append((name, args, result))
            if name == "find_nearby_help" and isinstance(result, dict) and result.get("needs_location"):
                # 시 전체만 말했고 위치가 없으면 기준을 임의로 정하지 않고 바로 묻는다
                ask = {"question": result["error"], "options": ["내 위치로 찾기"]}
                return {"text": ask["question"], "ask": ask, "tool_results": tool_results, "trace": trace}
            messages.append({"role": "tool", "tool_call_id": call.id, "content": _llm_view(name, result)})
    return {"text": "결과를 정리하지 못했어요. 다시 한 번 말씀해 주세요.", "ask": None,
            "tool_results": tool_results, "trace": trace}


# ---------- 인터넷·AI가 없을 때 쓰는 규칙 기반 모드 ----------
TYPE_WORDS = [("electric_wheelchair", "전동"), ("manual_wheelchair", "휠체어"),
              ("pregnant", "임산부|임신|임부|만삭|출산\\s*예정|태교"),
              ("stroller", "유모차|아기|애기|아가|아이|영유아|신생아|돌쟁이|아기띠"),
              ("senior", "어르신|부모님|할머니|할아버지|어머니|아버지|노인|무릎|보행기|지팡이|거동|오래 못 걸|걷기 힘|허리")]
THEME_WORDS = [("바다", "바다|해변|해안|포구"), ("마을", "마을|골목"), ("자연·숲", "숲|자연|꽃|산책"), ("역사·문화", "역사|문화|유적")]


def rule_mode(text, user_type=None, origin=None):
    import re
    if not user_type:
        user_type = next((k for k, p in TYPE_WORDS if re.search(p, text)), None)
    if not user_type:
        return {"text": "누구와 함께 가시나요?", "ask": {"question": "누구와 함께 가시나요?",
                "options": ["휠체어", "전동 휠체어", "유모차", "어르신", "임산부"]}, "tool_results": [],
                "trace": [{"tool": "ask_user", "args": {}}]}
    theme = next((k for k, p in THEME_WORDS if re.search(p, text)), None)
    area = None
    for w in re.findall(r"[가-힣]{2,4}", text):
        if T.find_area(w):
            area = w
            break
    args = {"user_type": user_type, "area": area, "theme": theme, "need_toilet": "화장실" in text}
    if origin:  # 시작 화면 '내 위치'를 고른 경우
        args.update({"area": None, "origin_lat": origin[0], "origin_lon": origin[1]})
    res = T.recommend_places(**args)
    if not res["results"]:
        return {"text": "조건에 맞는 곳을 찾지 못했어요. 동네나 분위기를 바꿔서 말해 보세요.", "ask": None,
                "tool_results": [("recommend_places", args, res)], "trace": [{"tool": "recommend_places", "args": args}]}
    top = res["results"][0]
    return {"text": f"**{top['place']}** 추천해요. {top['slope_say']}", "ask": None,
            "tool_results": [("recommend_places", args, res)], "trace": [{"tool": "recommend_places", "args": args}]}
