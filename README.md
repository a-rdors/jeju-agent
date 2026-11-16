# 제주 같이나들이

휠체어·유모차·어르신과 함께하는 제주 나들이를, 공공데이터 근거로 "갈 수 있을까, 뭘 조심할까"까지 알려주는 AI Agent.
제주 AI·빅데이터 활용 AI Agent 개발 챌린지 출품작.

## 빠른 실행

```powershell
# 1. 가상환경과 라이브러리
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt

# 2. 키 파일 만들기: 프로젝트 폴더에 .env 파일을 만들고 아래 두 줄을 넣는다
#    OPENAI_API_KEY=sk-...          (Agent 대화. 없으면 버튼 기반 기본 모드로 동작)
#    JEJU_PROJECT_KEY=...           (제주데이터허브 API. 현재 화면 실행에는 필요 없음)

# 3. 실행 (내 컴퓨터에서만 열림)
.venv\Scripts\streamlit run app/main.py --server.address localhost
```

브라우저에서 http://localhost:8501 을 연다.

## 폴더 구조

| 경로 | 내용 |
|---|---|
| `app/main.py` | 화면(Streamlit). **화면 작업은 이 파일만** 바꾸면 된다 |
| `app/agent.py` | Agent: OpenAI 함수 호출 반복, 시스템 프롬프트, 되묻기·날씨·위치 처리 |
| `app/tools.py` | 도구: 장소 추천·판정, 코스 상세, 의료, 식당, 날씨, 전화 질문지. 모든 판단은 코드로 계산 |
| `scripts/01~03` | 데이터 받기 → 문장을 접근성 표로 → 보조 표(동네·의료·영업 확인) |
| `scripts/04~05` | 시나리오 테스트(튜닝용 10개, 확인용 8개) |
| `data/raw` | 원본(제주데이터허브 무장애여행 정보, 상가·음식점·응급실) |
| `data/processed` | 정제 결과(Agent가 읽는 표) |
| `docs/` | 기획서, UX 흐름 설계, 검수·테스트 기록 |

## 데이터 다시 만들기

```powershell
.venv\Scripts\python scripts/01_download_mujangae.py   # 공개 무장애 데이터 150개 파일
.venv\Scripts\python scripts/02_build_access_table.py  # 문장 → 접근성 표 (2020 관광지 20곳은 data/raw/mujangae_extra)
.venv\Scripts\python scripts/03_build_support.py       # 동네·의료·영업 확인·식당 표
```

## 화면 작업하는 사람에게

- 결과 화면 순서와 쓸 수 있는 데이터 필드: `docs/UX_흐름_설계.md`
- 현재 위치: 지도에서 위치 권한을 받으면 `st.session_state.location = (위도, 경도)`만 넣으면 Agent가 "내 근처" 기준으로 찾는다
- 지도 표시용 좌표: `tools.get_place_detail(place)["all_points"]`
- 길안내: `tools.kakao_route_link(이름, 위도, 경도)` (키 불필요)

## 외부 서비스

| 서비스 | 용도 | 키 |
|---|---|---|
| OpenAI (gpt-5.4-mini) | 말 해석, 도구 선택, 쉬운 설명 | 필요 |
| Open-Meteo | 7일 날씨 예보 | 불필요 |
| 카카오맵 링크 | 길안내 열기 | 불필요 |

## 데이터 출처

제주데이터허브(jejudatahub.net): 제주특별자치도 무장애여행 정보, 제주특별자치도 음식점 목록(통합), 상가(상권) 정보, 제주 응급실 보유 병원 정보, 약국·버스 정류소 API.
무장애 현장 정보는 2020~2021년 조사 자료라 현재와 다를 수 있다.
