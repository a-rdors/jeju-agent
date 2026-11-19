// 지도 표식 공통 타입. 지도(KakaoMap)와 화면 상태(store)가 함께 쓴다.
export type MarkKind = "place" | "dot" | "caution" | "toilet" | "food" | "help";

export interface MapMark {
  kind: MarkKind;
  lat: number;
  lon: number;
  text?: string;
  /** 글자 대신 그릴 흰 그림(lib/icons.ts 의 FILL 경로) */
  icon?: string;
  name: string;
  sub: string;
  color: string;
  big?: boolean;
  /** 1순위 표식 위에 늘 떠 있는 뾰족한 이름 말풍선 */
  pin?: string;
  fit?: boolean;
  /** 바로 옆 표식과 겹칠 때 오른쪽으로 비켜 그릴 칸 수(표식 너비 단위) */
  nudge?: number;
  ring?: boolean;
  /** 장소 카드(나들이 장소·추천 장소)에 보일 주소와 대표 사진 */
  address?: string;
  photos?: string[];
  /** 나들이 장소 점의 동네 이름(애월·중문·제주시내 등). 멀리 볼 때 묶음 이름표에 쓴다 */
  area?: string;
}

export interface MapData {
  marks: MapMark[];
  route: [number, number][];
  /** 범례의 화장실 이름(휠체어 이용자면 '장애인 화장실', 아니면 '넓은 화장실') */
  toiletLabel?: string;
}

export interface PlaceDot {
  place: string;
  lat: number;
  lon: number;
  sigungu: string;
  dong: string;
  /** 일반정보의 주소(없으면 null) */
  address?: string | null;
  /** 대표 사진 경로(/photos/<n>/<i>.jpg) */
  photos?: string[];
}
