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

SYSTEM = """너는 '제주 같이나들이' 도우미야. 휠체어·유모차·어르신과 함께 제주 나들이를 준비하는 가족을 돕는다.

원칙
0. 너는 일반 여행 안내가 아니다. "어디 갈까"가 아니라 "이 가족이 거기 갈 수 있을까, 무엇을 조심해야 할까"에 답한다.
   접근성 근거(경사, 턱, 계단, 화장실, 주차, 쉼터)가 없는 추천은 하지 않는다.
1. 사용자가 가장 편해야 한다. 숫자(경사 몇 도, 몇 km)를 묻지 않는다. 일상어를 네가 해석한다.
2. ask_user는 이동 유형(누가 가는지)을 전혀 알 수 없을 때만 딱 한 번 쓴다.
   문장에 휠체어·전동·유모차·아기·할머니·부모님·어르신·무릎 같은 단서가 있거나 '이미 확인된 이동 유형'이 있으면 절대 묻지 않는다.
   분위기·지역·동행인·날짜는 묻지 않는다. 모르면 조건 없이 바로 찾는다.
3. 장소를 추천하려면 반드시 recommend_places를 먼저 호출한다. 도구 결과에 없는 장소·시설·사실은 절대 말하지 않는다.
4. 추천 답변은 짧게: 1등 장소 이름, 왜 맞는지 한두 문장, 조심할 점 한 문장. 나머지는 화면 카드가 보여준다.
5. 쉬운 말을 쓴다. "기준 초과" 같은 말 대신 "가파른 구간이 있어요"처럼 말한다.
6. 확인되지 않은 정보는 "확인이 안 돼요, 가기 전에 전화해 보세요"라고 말한다. 안전을 보장하는 말("안전해요")은 하지 않는다.
10. '다른 곳', '또 없어?'라고 하면 '이미 보여준 장소'를 exclude에 넣어 다시 recommend_places를 부른다.
7. '거기', '그곳', '그 근처'는 '직전 추천 장소'를 뜻한다. 다시 묻지 말고 그 장소 이름으로 도구를 부른다.
   사용자가 특정 장소의 길·화장실·쉼터를 물으면 get_place_detail, 약국·병원·응급은 find_nearby_help를 쓴다.
8. 식당·카페는 search_food를 쓴다. 제주 전체 식당이 대상이다(휠체어 진입은 배지일 뿐 필터가 아니다).
   휠체어 이용자 가족이면 prefer_wheelchair=true. wheelchair_only는 "휠체어로 들어갈 수 있는 곳만"이라고 할 때만.
   식사 조건(diet_needs, 여러 개 가능): 이가 안 좋다·씹기 힘들다·틀니 → soft / 소화·속·위장이 안 좋다 → gentle /
   매운 걸 못 먹는다 → mild / 해산물 알레르기 → no_seafood / 혈압·짜게 먹으면 안 된다 → low_salt / 아이·애기와 식사 → kids.
   어떤 장소나 가게 '근처'를 물으면 place에 그 이름을 그대로 넣는다(식당 이름도 된다). 동네를 말하면 area.
   결과에 anchor_not_found가 있으면 위치를 못 찾았다고 솔직히 말하고 동네 이름을 물어본다.
   맛 평가·순위·의학적 조언은 하지 않는다. why(업종·가게 이름으로 추정한 근거)를 쉬운 말로 전하고,
   메뉴와 건강 상태에 맞는지는 call_questions로 가게에 전화해 확인하라고 안내한다.

9. 날짜나 날씨를 말하면 시스템이 미리 날씨를 조회해 '참고 날씨'로 준다. 그 내용으로 판단한다.
   비 예보면 실내 장소를 함께 제안하고, 주의사항(tips)은 쉬운 말로 전달한다. 날씨 자체를 길게 설명하지 않는다.

이동 유형 해석: '휠체어'라고만 하면 종류를 묻지 말고 manual_wheelchair로 정한다(수동이 경사에 더 조심스러운 기준).
'전동' -> electric_wheelchair, '유모차/아기' -> stroller, '부모님/할머니/어르신/무릎' -> senior.
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
        "description": "장소의 코스 흐름: 출발점부터 주의 지점, 쉼터, 장애인 화장실 위치를 순서대로.",
        "parameters": {"type": "object", "properties": {
            "place": {"type": "string"}, "user_type": {"type": "string", "enum": list(T.USER_TYPES.keys())}},
            "required": ["place"]}}},
    {"type": "function", "function": {
        "name": "find_nearby_help",
        "description": "장소에서 가장 가까운 약국·병의원·응급실.",
        "parameters": {"type": "object", "properties": {"place": {"type": "string"}}, "required": ["place"]}}},
    {"type": "function", "function": {
        "name": "search_food",
        "description": "제주 식당·카페 찾기(약 1만 9천 곳). 식사 조건으로 고르고 휠체어 진입 확인 가게는 배지로 표시.",
        "parameters": {"type": "object", "properties": {
            "food_kind": {"type": "string", "enum": list(T.FOOD_KINDS.keys())},
            "diet_needs": {"type": "array", "items": {"type": "string", "enum": list(T.DIET_NEEDS.keys())}},
            "prefer_wheelchair": {"type": "boolean"},
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
}


def _llm_view(name, result):
    """모델에게는 필요한 만큼만 전달한다(전체 지점 목록은 화면에서만 사용)."""
    if name == "get_place_detail" and "all_points" in result:
        result = {k: v for k, v in result.items() if k != "all_points"}
    return json.dumps(result, ensure_ascii=False, default=str)


def available():
    return bool(os.getenv("OPENAI_API_KEY"))


WEATHER_WORDS = r"오늘|내일|모레|주말|토요일|일요일|[월화수목금]요일|비가|비 오|비오|날씨|바람"


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
        ask = {"question": "누구와 함께 가시나요?", "options": ["휠체어", "전동 휠체어", "유모차", "어르신"]}
        return {"text": ask["question"], "ask": ask, "tool_results": [], "trace": [{"tool": "ask_user", "args": ask}]}
    named = T.match_place(next((w for w in re.findall(r"[가-힣]{3,}", last_q) if T.match_place(w)), None))
    if named:
        system += f"\n사용자가 말한 장소: {named}. 이 장소에 갈 수 있는지 물으면 get_place_detail(place='{named}')로 확인한다."

    # 질문 속 가게·장소 이름을 동네 이름보다 먼저 찾는다('서귀포흑돈으로' → 가게 '서귀포흑돈', 동네 '서귀포' 아님)
    tokens = [re.sub(r"(으로|에서|에는|에|로|이랑|랑|하고|까지|부터|근처|쪽|은|는|을|를|도)$", "", w)
              for w in re.findall(r"[가-힣A-Za-z0-9]+", last_q)]
    said_place = None
    for tok in tokens:
        if len(tok) < 3:
            continue
        a = T.match_place(tok) or (lambda r: r[2] if r and re.sub(r"\s", "", r[2]) == tok else None)(T.resolve_anchor(tok))
        if a:
            said_place = a
            break
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
    messages = [{"role": "system", "content": system}] + history
    for _ in range(MAX_STEPS):
        resp = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOL_SPECS)
        msg = resp.choices[0].message
        if not msg.tool_calls:
            return {"text": msg.content or "", "ask": None, "tool_results": tool_results, "trace": trace}
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
            if name in ("recommend_places", "search_food") and said_area and not args.get("area") and not args.get("place"):
                args["area"] = said_area  # 사용자가 말한 동네를 모델이 빠뜨린 경우 코드가 채운다
            if (name in ("recommend_places", "search_food") and user_location and not said_area
                    and not args.get("area") and not args.get("place")):
                # 동네를 말하지 않았고 현재 위치가 있으면 '내 근처' 기준으로 찾는다
                args["origin_lat"], args["origin_lon"] = user_location
            try:
                result = TOOL_FUNCS[name](**args)
            except Exception as e:  # 도구 오류도 모델에 알려 다시 판단하게 한다
                result = {"error": f"{type(e).__name__}: {e}"}
            tool_results.append((name, args, result))
            messages.append({"role": "tool", "tool_call_id": call.id, "content": _llm_view(name, result)})
    return {"text": "결과를 정리하지 못했어요. 다시 한 번 말씀해 주세요.", "ask": None,
            "tool_results": tool_results, "trace": trace}


# ---------- 인터넷·AI가 없을 때 쓰는 규칙 기반 모드 ----------
TYPE_WORDS = [("electric_wheelchair", "전동"), ("manual_wheelchair", "휠체어"),
              ("stroller", "유모차|아기|애기|아가|아이|영유아|신생아|돌쟁이|아기띠"),
              ("senior", "어르신|부모님|할머니|할아버지|어머니|아버지|노인|무릎|보행기|지팡이|거동|오래 못 걸|걷기 힘|허리")]
THEME_WORDS = [("바다", "바다|해변|해안|포구"), ("마을", "마을|골목"), ("자연·숲", "숲|자연|꽃|산책"), ("역사·문화", "역사|문화|유적")]


def rule_mode(text, user_type=None):
    import re
    if not user_type:
        user_type = next((k for k, p in TYPE_WORDS if re.search(p, text)), None)
    if not user_type:
        return {"text": "누구와 함께 가시나요?", "ask": {"question": "누구와 함께 가시나요?",
                "options": ["휠체어", "전동 휠체어", "유모차", "어르신"]}, "tool_results": [],
                "trace": [{"tool": "ask_user", "args": {}}]}
    theme = next((k for k, p in THEME_WORDS if re.search(p, text)), None)
    area = None
    for w in re.findall(r"[가-힣]{2,4}", text):
        if T.find_area(w):
            area = w
            break
    args = {"user_type": user_type, "area": area, "theme": theme, "need_toilet": "화장실" in text}
    res = T.recommend_places(**args)
    top = res["results"][0]
    return {"text": f"**{top['place']}**을(를) 추천해요. {top['slope_say']}", "ask": None,
            "tool_results": [("recommend_places", args, res)], "trace": [{"tool": "recommend_places", "args": args}]}
