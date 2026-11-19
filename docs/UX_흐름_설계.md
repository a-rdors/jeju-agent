# 제주 같이나들이 UX 흐름 설계

화면(카카오맵 연동 포함)을 만드는 사람이 보는 문서다. 판단 로직은 `app/tools.py`, `app/agent.py`에 있고 화면은 `app/main.py`만 바꾸면 된다.

## 0. 이 서비스가 지켜야 할 한 가지

> 일반 여행 앱은 "어디 갈까"를 묻고, 같이나들이는 "우리 가족이 갈 수 있을까, 뭘 조심할까"에 답한다.

모든 화면은 이 질문에 답하는 순서로 배치한다. 이동 접근성(경사·턱·계단)은 산책로·관광지 중심으로 판단한다.
식당·카페는 제주 전체가 대상이고, 어르신·아이의 식사 불편(씹기, 소화, 매운 음식, 알레르기, 싱겁게)에 맞춰 고른다. 휠체어 진입 확인은 배지로 표시한다.

## 1. UX 원칙 (근거 포함, 중요한 순서)

| # | 원칙 | 이 서비스에서 | 근거 |
|---|---|---|---|
| 1 | 답을 먼저, 근거는 아래 | 결과 맨 위에 **판정 한 줄**(`verdict`) | [NN/g](https://www.nngroup.com/articles/less-chat-more-answer/) |
| 2 | 접근성은 3단계 + 미확인 회색 | 갈 만해요(초록) / 동행인 도움이 있으면 갈 만해요(주황) / 확인이 더 필요해요(회색). 색 + 아이콘 + 글자 함께 | [Wheelmap](https://en.wikipedia.org/wiki/Wheelmap.org) |
| 3 | 정보 없음을 "가능"처럼 보이지 않게 | `checks`에서 `known=false`는 회색 "확인 안 됨" | [PhocusWire 조사: 상담사 90%가 접근성 정보 불완전](https://www.phocuswire.com/news/online/fora-travel-advisors-flag-outdated-inconsistent-accessibility-data) |
| 4 | 항목마다 출처·기준일 | `source` 문자열을 결과 아래에 항상 표시 | [Google Maps 접근성 정보 출처](https://blog.google/products/maps/how-anyone-can-make-maps-more-accessible/) |
| 5 | 전화 확인 질문지를 핵심 기능으로 | `call_questions(user_type)` + 전화 버튼 | [장애인 여행 가이드](https://disability-wiki.pages.dev/daily-living/accessible-travel/) |
| 6 | AI가 확인한 것 공개 | `trace`(어떤 도구를 썼는지) + `checks` | [Microsoft HAX 11](https://www.microsoft.com/en-us/haxtoolkit/library/pattern/) |
| 7 | 되묻기는 최소, 버튼으로 | `ask.options`를 버튼으로. 최대 1~2번 | [NN/g 챗봇 가이드](https://www.nngroup.com/articles/ai-chatbots-design-guidelines/) |
| 8 | 빠른 답장 버튼 5개 이하, 짧은 동사형 | 후속 칩 4개 이내 | [SAP AI quick reply](https://www.sap.com/design-system/btp/patterns/generative-ai/ai-quick-reply/usage) |
| 9 | 첫 화면에 할 수 있는 일 + 예시 칩 | 대상 버튼 3개 + 예시 질문 칩 | [NN/g prompt suggestions](https://www.nngroup.com/articles/prompt-suggestions/) |
| 10 | 어르신: 큰 글씨, 높은 대비, 큰 버튼 | 본문 17px 이상, 대비 4.5:1 이상, 큰 글씨 모드 | [W3C 고령 사용자](https://www.w3.org/WAI/older-users/), [서울디지털재단 표준](https://m.boannews.com/html/detail.html?idx=96003) |
| 11 | 오류는 짧고 바로 복구 가능하게 | AI 연결 실패 시 자동으로 기본 모드, 문구 한 줄 | [NN/g 고령자 사용성](https://www.nngroup.com/articles/usability-for-senior-citizens/) |
| 12 | 위치 권한은 필요한 순간에, 이유와 함께 | "가까운 곳을 찾으려고 해요" + 거부 시 동네 선택 | [NN/g 권한 요청](https://www.nngroup.com/articles/permission-requests/) |
| 13 | 저장·공유 | 코스표 인쇄/공유, 카카오맵 길안내 | [NN/g](https://www.nngroup.com/articles/ai-chatbots-design-guidelines/) |

## 2. 사용자 흐름

1. **첫 화면**: "우리 가족이 갈 수 있는지 알려드려요" 한 줄 → [휠체어][유모차][어르신] 큰 버튼 → 예시 질문 칩 3~4개 → 입력창
2. **입력**: 버튼 한 번 또는 평소 말("아빠가 휠체어 타시는데 바다 보러 갈 만한 데")
3. **되묻기(필요할 때만)**: 누가 가는지 전혀 모를 때만 버튼 질문 1번. 지역·분위기·날짜는 묻지 않는다
4. **위치(선택)**: "내 근처" 같은 말이 있거나 지역이 없을 때 "가까운 곳을 찾으려고 위치를 써도 될까요?" → 허용 시 좌표 사용, 거부 시 [제주시][서귀포시][동네 입력]
5. **진행 표시**: "날씨 확인 → 장소 찾기"처럼 단계 표시(`trace`)
6. **결과**: 아래 3번 순서
7. **행동**: [카카오맵 길안내][전화 + 질문지][인쇄/공유]
8. **후속 칩**: [다른 곳 보기][근처 식당][병원·약국][비 오면?]

## 3. 결과 화면 순서

1. 판정 배지 + 한 줄 이유 (`verdict`, `verdict_color`, `verdict_reason`)
2. 장소 이름, 위치(시·동), 코스 시간·길이
   - 현장 사진 최대 3장(누르면 크게 보기). 사진이 없는 장소는 이 칸을 그리지 않는다
3. 지도: 코스 지점(`get_place_detail().all_points`), 주의 지점은 빨강, 화장실·쉼터 표시
4. 행동 버튼 줄: 길안내, 전화, 공유
5. 조심할 점 최대 3개 (`watch_out`, 날씨 `tips`)
6. 확인표: 항목 / 상태 / 확인 여부 (`checks`), 확인 안 된 칸은 회색
7. 코스 따라가기: "출발 후 약 130m · 오르막" (`key_points`)
8. 접힌 칸: 병원·약국·응급실, 들어갈 수 있는 식당, 전화 질문지
9. 출처·기준일 (`source`)

## 4. 화면에서 쓸 데이터 (함수 → 필드)

| 함수 (`app/tools.py`) | 주요 필드 |
|---|---|
| `recommend_places(user_type, area, theme, need_toilet, max_minutes, origin_lat, origin_lon)` | `results[]`: place, where, verdict, verdict_color, verdict_reason, checks, slope_level, slope_say, minutes, course_m, distance_km, accessible_toilet, accessible_parking, companion_advised, good_points, watch_out, lat, lon, source |
| `get_place_detail(place, user_type)` | all_points[](lat, lon, label, flags, at_m), key_points, verdict, checks |
| `find_nearby_help(place)` | help: 약국/병·의원/응급실 [] (name, km, address, phone) |
| `search_food(food_kind, area, place, diet_needs, prefer_wheelchair, origin_lat, origin_lon)` | 제주 전체 식당 대상. items[]: name, food_type, km, wheelchair_entry(배지), why(식사 조건 추정 근거), lat, lon / diet_labels, call_questions, anchor_not_found |
| `get_weather(place, area, when)` | rain_chance, wind_ms, temp, tips[] |
| `call_questions(user_type, diet_needs)` | 전화로 물을 질문 목록(이동 유형 + 식사 조건) |
| `kakao_route_link(name, lat, lon)` | 카카오맵 길안내 URL(키 불필요) |
| `GET /api/places` (`server/api.py`) | 장소 점: place, lat, lon, photos[](현장 사진 경로, `data/processed/place_info.csv`) |

대화는 `agent.run(history, known_user_type, last_place, user_location)`. 반환: `text`(짧은 답), `ask`(버튼 질문), `tool_results`(위 함수 결과), `trace`(확인한 단계).

**현재 위치**: 지도 왼쪽 '내 위치' 단추를 누르면 브라우저 위치 권한을 받아 `location = [위도, 경도]`를 저장하고(`web/lib/store.ts`의 `locateMe`), 대화 요청에 함께 보낸다. 사용자가 동네를 말하지 않았을 때 자동으로 "내 근처" 기준이 된다. 제주 밖이면 위치를 쓰지 않고 제주 전체를 보여 준다.

## 5. 하지 말 것

- 긴 글을 한 번에 쏟아내기(답은 짧게, 나머지는 카드·접힌 칸)
- 확인 안 된 정보를 초록색이나 "가능"으로 표시
- 첫 화면에서 바로 위치 권한 요구, 거부하면 막히는 흐름
- "안전해요"처럼 단정하는 말
- 작은 글씨, 연한 회색 글씨, 작은 버튼

## 6. 없는 것 (기대하지 말 것)

- 모든 장소의 사진: 코스 장소 70곳 중 50곳만 현장 사진이 있다(제주데이터허브 무장애여행 정보). 나머지 20곳은 사진 칸이 없다
- 휠체어 길찾기 경로: 카카오·네이버 모두 제공하지 않음. 길안내는 일반 경로이고, 접근성 판단은 조사 지점 기준
- 실시간 혼잡도·영업시간
