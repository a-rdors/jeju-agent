// 지도 표식 공통 타입. 지도(KakaoMap)와 화면 상태(store)가 함께 쓴다.
export type MarkKind = "place" | "dot" | "caution" | "toilet" | "food" | "help";

export interface MapMark {
  kind: MarkKind;
  lat: number;
  lon: number;
  text?: string;
  name: string;
  sub: string;
  color: string;
  big?: boolean;
  fit?: boolean;
  ring?: boolean;
  /** 장소 카드(나들이 장소·추천 장소)에 보일 주소와 대표 사진 */
  address?: string;
  photos?: string[];
}

export interface MapData {
  marks: MapMark[];
  route: [number, number][];
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
