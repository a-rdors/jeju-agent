import type { Metadata, Viewport } from "next";
import "./globals.css";

const PRETENDARD =
  "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css";

export const metadata: Metadata = {
  title: "제주 같이나들이 — 휠체어·유모차·어르신과 함께 가는 제주",
  description: "휠체어·유모차·어르신과 함께 가는 제주. 경사·계단·턱, 장애인 화장실과 쉴 곳까지 먼저 살펴보고 알려드려요.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover", // 휴대폰 노치·홈 막대 자리(safe-area)를 CSS 에서 직접 비켜 간다
  interactiveWidget: "resizes-content", // 자판이 올라오면 대화창 높이가 줄어든다(안드로이드 크롬)
  themeColor: "#2E3135",
  colorScheme: "light",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ko">
      <head>
        <link rel="preconnect" href="https://cdn.jsdelivr.net" crossOrigin="anonymous" />
        <link rel="stylesheet" href={PRETENDARD} />
      </head>
      <body>{children}</body>
    </html>
  );
}
