import type { NextConfig } from "next";

// 파이썬 API(FastAPI, server/api.py) 주소. 배포할 때는 API_ORIGIN 으로 바꾼다.
const API_ORIGIN = process.env.API_ORIGIN ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // create-next-app 기본값 그대로 둔다. 이 앱은 한 페이지짜리 클라이언트 앱이라 서버에서 읽는 데이터가 없고
  // (상태·fetch 는 모두 브라우저에서), 서버는 빈 틀(static shell)만 미리 그리므로 두 옵션이 동작을 바꾸지 않는다.
  cacheComponents: true,
  partialPrefetching: true,
  // 개발용 "N" 표시가 폰 화면에서 대화 입력창을 가려서 끈다(오류 표시는 그대로 나온다).
  devIndicators: false,
  experimental: {
    // rewrites 프록시 기본 제한은 30초. AI가 도구를 여러 번 부르면 더 걸릴 수 있어 넉넉히 둔다.
    proxyTimeout: 120_000,
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_ORIGIN}/api/:path*` }];
  },
};

export default nextConfig;
