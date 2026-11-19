# 제주 같이나들이 UX 흐름 설계

화면(카카오맵 연동 포함)을 만드는 사람이 보는 문서다. 판단 로직은 `app/tools.py`, `app/agent.py`에 있고, API는 `server/api.py`, 화면은 `web/`(Next.js)이다.
화면 상태와 동작은 `web/lib/store.ts`, 지도 표식은 `web/lib/mapData.ts`, 색·크기 토큰은 `web/DESIGN.md`와 `web/app/globals.css`에 있다.

## 0. 이 서비스가 지켜야 할 한 가지

> 일반 여행 앱은 "어디 갈까"를 묻고, 같이나들이는 "우리 가족이 갈 수 있을까, 뭘 조심할까"에 답한다.

모든 화면은 이 질문에 답하는 순서로 배치한다. 이동 접근성(경사·턱·계단)은 산책로·관광지 중심으로 판단한다.
식당·카페는 제주 전체가 대상이고, 어르신·아이의 식사 불편(씹기, 소화, 매운 음식, 알레르기, 싱겁게)에 맞춰 고른다. 휠체어 진입 확인은 배지로 표시한다.

## 1. UX 원칙 (근거 포함, 중요한 순서)

| # | 원칙 | 이 서비스에서 | 근거 |
|---|---|---|---|
| 1 | 답을 먼저, 근거는 아래 | 장소 이름 바로 아래 **판정 알약**(`verdict`). 대화 답은 1순위 하나만 짧게 | [NN/g](https://www.nngroup.com/articles/less-chat-more-answer/) |
| 2 | 접근성은 3단계 + 미확인 회색 | 갈 만해요(초록 #2F7A4D) / 동행인 도움이 있으면 갈 만해요(파랑 #2C6EA6, 코드 값은 `orange`) / 확인이 더 필요해요(회색 #5E6368). 색 + 아이콘 + 글자 함께. 지도 번호·후보 단추도 같은 색(`VERDICT_HEX`) | [Wheelmap](https://en.wikipedia.org/wiki/Wheelmap.org) |
| 3 | 정보 없음을 "가능"처럼 보이지 않게 | `checks`에서 `known=false`는 회색 "확인 안 됨" | [PhocusWire 조사: 상담사 90%가 접근성 정보 불완전](https://www.phocuswire.com/news/online/fora-travel-advisors-flag-outdated-inconsistent-accessibility-data) |
| 4 | 항목마다 출처·기준일, 필요할 때 펼쳐서 | 판정 옆 `근거 보기`(조사 원문·기준일, `evidence`), `자세히 ›`(확인표·출처), `코스` 탭 아래 `source`. 늘 깔아 두지 않는다 | [Google Maps 접근성 정보 출처](https://blog.google/products/maps/how-anyone-can-make-maps-more-accessible/) |
| 5 | 전화로 확인할 것을 짧게 | 대화 답의 '확인할 점:' 한 줄(번호가 있으면 눌러서 전화), 일정표의 '가기 전 전화로 확인할 것'(`call_questions`) | [장애인 여행 가이드](https://disability-wiki.pages.dev/daily-living/accessible-travel/) |
| 6 | AI가 확인한 것 공개 | 판정에 쓴 조사 원문(`근거 보기`)과 시설 확인표로 보여 준다. 도구 기록(`trace`)은 API가 돌려주지만 화면에 그리지 않는다 | [Microsoft HAX 11](https://www.microsoft.com/en-us/haxtoolkit/library/pattern/) |
| 7 | 되묻기는 최소, 버튼으로 | `ask.options`를 버튼으로. 누가 가는지 전혀 모를 때, 시 이름만 말하고 병원·약국을 물을 때(`내 위치로 찾기`)만 | [NN/g 챗봇 가이드](https://www.nngroup.com/articles/ai-chatbots-design-guidelines/) |
| 8 | 빠른 답장 대신 고정된 이동 단추 | 후속 칩을 두지 않는다. 탭 4개, 후보 번호 1~3, ↻ 하나로 다음 행동을 고른다 | [SAP AI quick reply](https://www.sap.com/design-system/btp/patterns/generative-ai/ai-quick-reply/usage) |
| 9 | 첫 화면에 할 수 있는 일 + 예시 | 카드 4장(`찾기`) + 동네 칩 5개. 예시 질문 4개는 빈 대화창에 | [NN/g prompt suggestions](https://www.nngroup.com/articles/prompt-suggestions/) |
| 10 | 어르신: 큰 글씨, 높은 대비, 큰 버튼 | 본문 17px, 대비 4.5:1 이상, `큰 글씨`(125%), 글자를 함께 쓴 큰 단추 | [W3C 고령 사용자](https://www.w3.org/WAI/older-users/), [서울디지털재단 표준](https://m.boannews.com/html/detail.html?idx=96003) |
| 11 | 오류는 짧고 바로 복구 가능하게 | 키가 없으면 조용히 기본 모드. AI 오류일 때만 문구 한 줄. 지도 실패는 지도 자리에 한 줄 | [NN/g 고령자 사용성](https://www.nngroup.com/articles/usability-for-senior-citizens/) |
| 12 | 위치 권한은 사용자가 누를 때만 | 지도 왼쪽 내 위치 단추, 또는 대화의 `내 위치로 찾기`. 첫 화면에서 묻지 않고, 거부해도 동네 칩·말로 계속 쓴다 | [NN/g 권한 요청](https://www.nngroup.com/articles/permission-requests/) |
| 13 | 저장·길안내 | `길안내`(카카오맵), `전화`, 반나절 일정이면 `일정표 내려받기`(HTML, 인쇄·PDF) | [NN/g](https://www.nngroup.com/articles/ai-chatbots-design-guidelines/) |

## 2. 사용자 흐름

1. **첫 화면**: 지도는 섬 전체(지역 이름표). 패널에 "함께 가도 괜찮을지, 먼저 알려 드려요" → `어디쯤 가세요?` 동네 칩(`상관없어요`·`제주시`·`애월·한림`·`중문·서귀포`·`성산·구좌`, 고르면 지도가 그쪽으로 다가간다) → 카드 4장(휠체어 타는 가족·아기와 유모차·걷기 힘든 어르신·임신 중인 가족)마다 `찾기`. 오른쪽 아래 하르방 단추와 '하르방에게 물어보세요!'
2. **입력**: 카드 `찾기`(AI를 거치지 않고 `rule_mode`로 바로 찾는다. 대화창에 말을 남기지 않는다) 또는 대화창에 평소 말("아빠가 휠체어 타시는데 바다 보러 갈 만한 데")
3. **되묻기(필요할 때만)**: 누가 가는지 전혀 모를 때만 버튼 질문 1번. 지역·분위기·날짜는 묻지 않는다
4. **위치(선택)**: 내 위치 단추 → 제주 안이면 지도를 옮기고 파란 점, `location` 저장, 처음 화면에 "현재 위치를 기준으로 가까운 곳부터 찾아 드릴게요." 동네 칩을 고르면 위치 기준을 지운다. 제주 밖이면 한 줄 안내 후 제주 전체. 병원·약국을 시 이름만으로 물으면 `내 위치로 찾기` 단추
5. **진행 표시**: 지도 위 "하르방이 길을 살펴보고 있어요". 대화창에는 질문 종류(병원·식당·날씨·장소·그 밖)에 맞춘 고정 문구 3개(`LOADING_STEPS`, `Chat.tsx`)
6. **결과**: 패널은 `한눈에` 탭(아래 3번 순서), 지도는 추천 번호와 고른 곳 이름표. 식당 답이면 식당 목록, 다른 장소·병원 답이면 장소 정보 화면(`처음 화면으로` / `○○ 결과로 돌아가기`)
7. **행동**: `길안내`, `전화`, `코스`. 가게·병원 카드는 `길안내`·`전화`·`지도`. 반나절 일정이면 답 아래 `일정표 내려받기`
8. **이어서**: 탭(`한눈에 · 코스 · 식당 · 병원·약국`), 후보 번호, ↻(본 곳 빼고 새로 찾기, "다른 곳 추천해 줘"를 보낸다), 대화로 더 묻기. `처음으로`는 큰 글씨·패널 열림·시트 높이만 남기고 처음 화면으로

## 3. 결과 화면 순서

지도는 화면 전체 배경이고, 패널(휴대폰은 아래 시트)이 그 위에 뜬다. `한눈에` 탭 순서:

1. 조건 한 줄: 이동 유형 · 식사 조건 · 날짜 · '○○ 기준' (`conditionTexts`)
2. 후보 번호 단추 1~3(판정 색, 지도 번호와 같음) + 끝에 ↻
3. 탭 4개
4. 장소 이름, 위치(시·동)
5. 현장 사진 최대 3장(누르면 크게 보기). 사진이 없는 장소는 이 칸을 그리지 않는다
6. 판정 알약 + `근거 보기`(코스 장소는 `근거 보기 · 조사 지점 N곳`). 펼치면 판정에 쓴 지점 먼저, `나머지 N곳 더 보기`
7. 시설 목록: 길 경사·코스 시간·길이(코스 장소) 또는 입구(관광공사 장소), 화장실, 주차, 있으면 좋은 것(`checks`, `good_points`)
8. 조심할 점 최대 2개: 초록이 아니면 `verdict_reason`이 첫 줄, 그다음 동행인 권유, `watch_out`. 초록이면 이유 줄을 따로 두지 않는다
9. 날씨 줄(날짜·비 %·기온). 비 50% 이상이면 "실내라면 ○○"(`rain_alt`)
10. `자세히 ›`: 접힌 칸. 제목 줄에 가까운 버스 정류소, 펼치면 확인표(`checks`)와 출처
11. 단추 줄: `길안내`, `전화`(번호가 있을 때), `코스`(코스 장소만)

다른 탭:
- **코스**: 시간·경사, 코스 따라가기(`key_points`, "출발 후 약 130m"), 가까운 장애인 화장실(`toilets_near`, `관리기관 전화`), `source`. 관광공사 장소는 "이곳은 코스 조사 자료가 없어요"
- **식당**: 장소 근처 식당 카드(`/api/food`), 접힌 칸 `이 장소 주변 가게 (2021 조사)`(`/api/nearby`)
- **병원·약국**: 약국·병·의원·응급실만. 화장실은 코스 탭에서 보여 준다

**지도 표식**(`buildMapData`):
- 추천 번호(판정 색. 고른 곳만 크게 + 이름표), 코스 선(파랑 #2F6FD6), 조심할 곳 빨간 !(#B83227), 장애인 화장실(청록 #0E8A8A). 쉼터 표식은 없다
- 식당(#E07A1C)은 `식당` 탭, 병원·약국(#5B3A8C)은 `병원·약국` 탭일 때만(대화 답 화면에서도)
- 처음 화면: 나들이 장소 점(이웃 지역끼리 초록·감귤 번갈아). 섬 전체를 볼 때는 '애월 16곳'처럼 지역 이름과 곳 수가 적힌 이름표가 뜨고, 누르면 그 지역으로 다가가 장소 점과 이름이 보인다
- 장소 점·번호를 누르면 장소 카드(사진·이름·주소, `자세히 살펴보기`·`길안내`). 가게·병원·조심할 곳은 짧은 말풍선
- 범례는 지금 보이는 표식만. 첫 화면에는 범례가 없다. 확대·축소 단추는 PC만

**같은 곳 가리키기**(`selected`, `focus`):
- 하르방이 답에서 먼저 말한 장소(`firstMentioned`)를 `selected`로 둔다. 패널, 지도의 큰 번호, 대화 후보 첫 단추가 같은 곳이다. 가게·병원도 먼저 말한 곳을 목록 맨 앞(`추천 1`)과 `focus`로
- 지도 표식, 패널 카드 `지도`, 대화 `지도` 어디서 골라도 `focusItem`: 지도 말풍선과 이름표, 패널 카드 강조·스크롤. 휴대폰에서 대화 단추로 고르면 대화창을 닫는다
- 이름표는 한 번에 하나. 가게·병원을 고른 동안은 장소 이름표를 숨긴다

**휴대폰**(639px 이하):
- 패널은 아래 시트(`sheet`: half/full). 손잡이를 누르면 크게·작게, 끌면 높이를 바꾼다. 화면 28% 아래로 내리면 닫히고, 66% 위면 full
- 시트 높이를 `--dash-h`로 알려 하르방 단추·말풍선이 시트 윗변을 따라온다. 위쪽 자리가 170px이 안 되면 `sheet-tall`: 내 위치 단추·말풍선은 숨기고 하르방 단추는 오른쪽 아래로
- 대화창은 화면 전체를 덮고, 열린 동안 하르방·내 위치 단추를 숨긴다. 첫 화면 그림은 빼고, 후보 번호는 한 줄로 옆으로 민다

## 4. 화면에서 쓸 데이터 (함수 → 필드)

| 함수 (`app/tools.py`) | 주요 필드 |
|---|---|
| `recommend_places(user_type, area, theme, need_toilet, max_minutes, limit=3, origin_lat, origin_lon, exclude, with_evidence=True)` | `results[]`: place, where, verdict, verdict_color, verdict_reason, checks, slope_level, slope_say, minutes, course_m, distance_km, accessible_toilet, accessible_parking, companion_advised, good_points, watch_out, lat, lon, phone, base_date, data_kind, evidence, source. 1순위에만 rain_alt / area_understood, note |
| `get_place_detail(place, user_type)` | all_points[](lat, lon, label, flags, at_m), key_points, verdict, checks, toilets_near, bus_stops, rain_alt, evidence, base_date, source |
| `find_nearby_help(place, kinds, user_type, origin_lat, origin_lon)` | help: 약국/병·의원/응급실(임산부면 산부인과)/장애인 화장실/기저귀 교환대 [] (name, km, address, phone, status, lat, lon), bus. 시 이름만이면 needs_location |
| `search_food(food_kind, area, place, diet_needs, prefer_wheelchair, wheelchair_only, limit=5, origin_lat, origin_lon, radius_km, avoid_upstairs)` | 제주 전체 식당 대상. items[]: name, food_type, km, phone, wheelchair_entry(배지), floor_note, why(식사 조건 추정 근거), lat, lon / around, diet_labels, call_questions, note, anchor_not_found |
| `check_nearby_places(place, limit=6)` | 2021 조사 주변 가게 items[]: name, category, km, open_status, wheelchair_entry |
| `get_weather(place, area, when)` | available, date, rain_chance, wind_ms, temp, tips[] |
| `plan_outing(user_type, area, theme, diet_needs, with_cafe, need_toilet, origin_lat, origin_lon, exclude)` | stops[](장소 → 식당 → 카페), legs. API가 `itinerary_html()`로 만든 `html`을 붙인다 |
| `call_questions(user_type, diet_needs)` | 전화로 물을 질문 목록. 질문지로 그리지 않고 '확인할 점' 한 줄과 일정표에 쓴다 |
| `kakao_route_link(name, lat, lon)` | 카카오맵 길안내 URL(키 불필요) |

| API (`server/api.py`) | 내용 |
|---|---|
| `GET /api/config` | kakao_js_key, ai, user_types, food_kinds, diet_needs. 지도 키도 여기서 받으므로 API가 꺼지면 지도도 뜨지 않는다 |
| `GET /api/places` | 장소 점: place, lat, lon, sigungu, dong, address, photos[](현장 사진 경로, `data/processed/place_info.csv`) |
| `GET /api/detail`, `/api/help`, `/api/food`, `/api/nearby`, `/api/weather` | 탭·지도가 AI 없이 바로 부르는 도구 결과(캐시) |
| `POST /api/chat` | 요청: text, user_type, history, known_user_type, last_place, location, shown_places. 응답: text, ask, tool_results[{name, args, result}], trace, fallback |

대화는 `agent.run(history, known_user_type, last_place, user_location, shown_places)`. 반환: `text`(짧은 답), `ask`(버튼 질문), `tool_results`(위 함수 결과), `trace`(화면에 쓰지 않음). 요청에 `user_type`이 있거나(카드 `찾기`) `OPENAI_API_KEY`가 없으면 `rule_mode(text, user_type, origin)`로 장소 추천만 한다. 이때 `shown_places`는 쓰지 않는다. AI 호출이 실패하면 `rule_mode` 결과 앞에 "(AI 연결이 안 돼서 기본 모드로 찾았어요)"를 붙인다.

**현재 위치**: 지도 왼쪽 내 위치 단추를 누르면 브라우저 위치 권한을 받아 `location = [위도, 경도]`를 저장하고(`web/lib/store.ts`의 `locateMe`), 대화 요청에 함께 보낸다. 사용자가 동네를 말하지 않았을 때 자동으로 "내 근처" 기준이 된다. 처음 화면에서 동네 칩을 고르면 `location`을 지운다. 제주 밖이면 위치를 쓰지 않고 제주 전체를 보여 준다. 대화의 `내 위치로 찾기`(`locateAndRetry`)는 위치를 받은 뒤 방금 질문을 다시 보낸다.

## 5. 하지 말 것

- 긴 글을 한 번에 쏟아내기(답은 짧게, 나머지는 카드·접힌 칸)
- 확인 안 된 정보를 초록색이나 "가능"으로 표시
- 첫 화면에서 바로 위치 권한 요구, 거부하면 막히는 흐름
- 지도·패널·대화가 서로 다른 곳을 가리키게 두기
- 휠체어를 말하지 않은 사람에게 '장애인 화장실·장애인 주차'라고 쓰기(대신 '넓은 화장실·주차장')
- "안전해요"처럼 단정하는 말
- 작은 글씨, 연한 회색 글씨, 작은 버튼, 이모지(아이콘을 쓴다)

## 6. 없는 것 (기대하지 말 것)

- 모든 장소의 사진: 코스 장소 70곳 중 50곳만 현장 사진이 있다(제주데이터허브 무장애여행 정보). 나머지 20곳은 사진 칸이 없다
- 휠체어 길찾기 경로: 카카오·네이버 모두 제공하지 않음. 길안내는 일반 경로이고, 접근성 판단은 조사 지점 기준
- 쉼터 지도 표식, 화면 속 전화 질문지, 공유 단추: 없다. 일정은 일정표 HTML을 내려받아 보낸다
- 실시간 혼잡도·영업시간
