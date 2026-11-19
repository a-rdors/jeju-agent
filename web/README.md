# 제주 같이나들이 웹 (Next.js)

제주 같이나들이 화면(Next.js 16)이다. 지도·추천·대화는 모두 파이썬 API(`server/api.py`)를 부른다.

## 실행

터미널 두 개를 연다.

1. API (저장소 맨 위 폴더에서)

   ```bash
   .venv/Scripts/python -m uvicorn server.api:app --reload --port 8000
   ```

2. 웹

   ```bash
   cd web
   npm install   # 처음 한 번
   npm run dev
   ```

브라우저에서 http://localhost:3000 을 연다. 웹의 `/api/...` 요청은 `next.config.ts` rewrites 가 `http://localhost:8000/api/...` 로 넘긴다(다른 주소면 `API_ORIGIN` 환경 변수).

## 카카오맵

카카오 개발자 콘솔 > 내 애플리케이션 > 플랫폼 > Web 에 **http://localhost:3000** 을 등록해야 지도가 뜬다(카카오맵 사용 설정 ON). 키는 저장소 맨 위 `.env` 의 `KAKAO_JS_KEY` 를 API가 `/api/config` 로 넘겨 준다.

## 확인

```bash
npx tsc --noEmit
npm run lint
npm run build
```

## 폴더

- `app/` 틀(`layout.tsx`, `page.tsx`)과 전체 CSS(`globals.css`)
- `components/` 상단 바(`TopBar.tsx`), 대시보드(`Dashboard.tsx`: 시작·결과·식당·장소 답), 내 일정 패널과 `+ 일정` 단추(`Plan.tsx`), 하르방 버튼과 대화창(`Chat.tsx`, 일정표 내려받기), 지도(`KakaoMap.tsx`), 내 위치 단추(`Locate.tsx`), 근거 보기(`Evidence.tsx`), 현장 사진(`Photos.tsx`), 화면 조각(`bits.tsx`), 아이콘(`Icon.tsx`), 대화 글 꾸밈(`Markdown.tsx`)
- `lib/store.ts` 화면 상태와 `send()` 규칙, `lib/api.ts` API 호출, `lib/useApi.ts` 결과 저장, `lib/plan.ts` 내 일정(이 브라우저 localStorage `jeju-plan-v1`, 최대 10곳), `lib/mapData.ts` 지도 표식, `lib/types.ts` 지도 표식 타입, `lib/art.ts` 그림, `lib/icons.ts` 아이콘 경로
