# 제주 같이나들이 API 서버

## 실행 방법

저장소 루트에서 아래 명령어를 실행하세요.

```bash
.venv/Scripts/python -m uvicorn server.api:app --reload --port 8000
```

- API 기본 URL: `http://localhost:8000`
- 자동 문서: `http://localhost:8000/docs`

## 주요 엔드포인트

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/api/config` | Kakao 키, AI 사용 여부, 이동 유형 목록 등 |
| GET | `/api/places` | 제주 나들이 장소 247곳(지도 점. 있는 곳은 주소·현장 사진 포함) |
| POST | `/api/chat` | 대화 처리(AI 또는 규칙 모드). 반나절 일정이면 일정표 HTML(`html`)을 붙여 보냄 |
| GET | `/api/detail` | 장소 코스 상세 정보 |
| GET | `/api/help` | 근처 약국·병원·응급실, 장애인 화장실·기저귀 교환대·버스 정류소 |
| GET | `/api/food` | 근처 식당 검색 |
| GET | `/api/nearby` | 주변 가게 목록 |
| GET | `/api/weather` | 날씨 예보 |
| GET | `/api/questions` | 가기 전 전화 질문지 |
| GET | `/api/route-link` | 카카오맵 길안내 URL |

## CORS

`http://localhost:3000` 및 `http://127.0.0.1:3000`에서의 요청을 허용합니다.
