# 판정 근거 펼치기: `evidence` 필드 (백엔드 완료, 화면은 웹 세션 담당)

판정(갈 만해요 / 동행인 도움이 있으면 갈 만해요 / 확인이 더 필요해요) 아래에 "근거 보기"를 펼치면
그 판정 뒤에 있는 공공데이터 기록 원문을 보여 준다.

## 어디에 붙나 (기존 필드는 그대로, `evidence`만 추가)
- `POST /api/chat` → `tool_results[i].result.results[j].evidence` (`name === "recommend_places"`일 때 각 장소)
- `GET /api/detail` → 최상위 `evidence` (`get_place_detail` 결과, 코스·시설 공통)
- `/api/places`, `all_points`, `key_points`, `checks` 모양은 바뀌지 않았다.
- `rain_alt`, `plan_outing`의 `stops`에는 없다(필요하면 `/api/detail`로 불러온다).
- 장소를 못 찾으면 `evidence: null`이 올 수 있다(정상 결과에서는 항상 객체).
- 모델(LLM)에게는 넘기지 않는다(`agent._llm_view`가 뺀다). 그래서 답변 글에는 안 나오고 화면 전용이다.

## 모양
```ts
// web/lib/types.ts 에 추가할 초안
export interface EvidenceItem {
  label: string;          // 지점 이름 또는 항목 이름. 코스: "정자 앞" / 시설: "출입 경로", "장애인 화장실" …
  text: string;           // 조사 원문 그대로(바꿔 쓰지 않음). 예: "정자 앞 | 정자 입구 계단 3개"
  flags: string[];        // 코스 지점 표시: "경사 약 9도", "턱 11.5cm", "계단", "진입 어려움", "도움 필요",
                          //   "장애인 화장실", "장애인 주차". 시설 항목은 항상 [].
  at_m: number | null;    // 코스 출발점에서 걸은 거리(m, 10m 단위). 코스 옆 지점·시설 항목은 null.
  on_route: boolean | null; // 코스 위 지점 true, 코스 옆 지점 false, 시설 항목 null.
  used: boolean;          // 판정에 실제로 쓴 기록이면 true(코스: 경사·계단·턱·막힘이 있는 코스 위 지점,
                          //   시설: 출입 경로(없으면 출입문) + 장애인 화장실이 있을 때 화장실). 강조 표시용.
  lat: number | null;     // 코스 지점 좌표(지도에 찍을 때). 시설 항목은 null.
  lon: number | null;
}

export interface Evidence {
  kind: "course" | "facility";  // course: 제주도 코스 조사 / facility: 관광공사 시설 정보
  summary: string;        // 펼치기 버튼 옆 한 줄. 예: "이 코스 조사 지점 10곳 확인 · 판정에 쓴 지점 4곳"
                          //   / "관광공사 시설 정보 7개 항목 확인 · 판정에 쓴 항목 2개"
  source: string;         // "제주데이터허브 무장애여행 위치정보" | "한국관광공사 무장애 여행 정보"
  survey: string;         // "2021 마을·해안길 조사" | "2020 관광지 조사" | "관광공사 무장애 여행 정보"
  base_date: string;      // 코스: "2021-12-22" 같은 조사일 / 시설: "관광공사 API(수시 갱신)"
  used_count: number;     // items 중 used=true 개수
  items: EvidenceItem[];  // 순서: used=true 먼저(코스 순서대로), 그다음 나머지 코스 위 지점, 마지막에 코스 옆 지점
}

// 기존 타입에 optional 로 추가
// interface PlaceResult { ...; evidence?: Evidence | null }   // recommend_places results[j]
// interface PlaceDetail { ...; evidence?: Evidence | null }   // /api/detail
```

## 예 (가문동해안길, 줄임)
```json
{
  "kind": "course",
  "summary": "이 코스 조사 지점 10곳 확인 · 판정에 쓴 지점 4곳",
  "source": "제주데이터허브 무장애여행 위치정보",
  "survey": "2021 마을·해안길 조사",
  "base_date": "2021-12-22",
  "used_count": 4,
  "items": [
    {"label": "시작(출발지점) 하귀포구 화장실", "text": "시작(출발지점) 하귀포구 화장실 | 화장실 입구 단차 8cm. 화장실 진입시 경계석 높이 11.5cm",
     "flags": ["턱 11.5cm"], "at_m": 0, "on_route": true, "used": true, "lat": 33.486813, "lon": 126.392287},
    {"label": "정자 앞", "text": "정자 앞 | 정자 입구 계단 3개", "flags": ["계단"], "at_m": 40, "on_route": true, "used": true, "lat": 33.486584, "lon": 126.392576},
    {"label": "방파제 입구", "text": "방파제 입구 | 단차 있음", "flags": [], "at_m": 80, "on_route": true, "used": false, "lat": 33.486405, "lon": 126.393033}
  ]
}
```

## 화면 메모
- 코스 하나에 지점이 6~49곳이다. 처음엔 `used=true` 항목만 보이고 "나머지 n곳 더 보기"로 펼치면 길이가 적당하다.
- 시설(`kind: "facility"`)은 항목이 최대 9개라 한 번에 다 보여도 된다.
- 출처 표기: `${source}(${survey}, ${base_date} 기준)`. 시설은 `base_date`가 날짜가 아니라 "관광공사 API(수시 갱신)"다.
- `text`는 원문이라 휠체어 기준 문구("휠체어 접근 가능함")가 그대로 있다. 판정 문장(`verdict_reason`)은 이미 사용자에 맞게 바꿔 쓴다.
