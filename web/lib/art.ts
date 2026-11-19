// 그림(SVG). app/ui.py 의 하르방·귤·시작 그림·아이콘을 그대로 옮겼다.
// <img src="data:..."> 로 쓰므로 그림 안의 <style>(눈 깜빡임)도 그대로 움직이고, 패턴 id가 서로 부딪히지 않는다.

export function dataUri(svg: string) {
  const s = svg.includes('xmlns="http://www.w3.org/2000/svg"')
    ? svg
    : svg.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ');
  return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(s);
}

export const ICON: Record<string, string> = {
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>',
  people: '<svg viewBox="0 0 24 24" fill="#fff"><circle cx="8" cy="7.5" r="3.2"/><circle cx="16.5" cy="8.5" r="2.6"/><path d="M2.5 19c0-3.4 2.5-6 5.5-6s5.5 2.6 5.5 6z"/><path d="M13.6 19c.2-2.2-.4-3.9-1.5-5.2.9-.6 2.1-1 3.4-1 3 0 5 2.4 5 5.6V19z"/></svg>',
  question: '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round"><path d="M9 9.2a3 3 0 1 1 4.3 2.7c-.9.5-1.3 1.1-1.3 2.1"/><circle cx="12" cy="17.6" r=".6" fill="#fff"/></svg>',
  wheel: '<svg viewBox="0 0 24 24" fill="none" stroke="#1E5636" stroke-width="2" stroke-linecap="round"><circle cx="10" cy="4" r="1.6" fill="#1E5636"/><path d="M10 7v6h6l2.5 5"/><path d="M10 10h5"/><path d="M7.5 11.5a5 5 0 1 0 7 5.8"/></svg>',
  stroller: '<svg viewBox="0 0 24 24" fill="none" stroke="#9C4A07" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5h2l1.5 7h10a6 6 0 0 0-6-6V5"/><path d="M7.5 12c.5 2.5 2.5 3.5 5 3.5h3"/><circle cx="9" cy="19" r="1.8"/><circle cx="16.5" cy="19" r="1.8"/></svg>',
  senior: '<svg viewBox="0 0 24 24" fill="none" stroke="#2C6EA6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="4" r="1.8" fill="#2C6EA6"/><path d="M11 7l-1.5 6 3 3 1 5"/><path d="M9.5 13l-2.5 8"/><path d="M11 8.5l3 2.5"/><path d="M17 11v10"/><path d="M15.5 11.2c.4-.6 1-1 1.5-1"/></svg>',
  pregnant: '<svg viewBox="0 0 24 24" fill="none" stroke="#A8326E" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="4" r="1.8" fill="#A8326E"/><path d="M11 7.5c-1.6 1.2-2 3.2-1.6 5.3"/><path d="M11 7.5c1 .6 1.4 1.5 1.5 2.6 2.6.6 3.6 2.7 3 4.7-.5 1.6-2.1 2.4-4 2.4"/><path d="M9.6 12.8L8.8 21"/><path d="M11.8 17.2l.6 3.8"/></svg>',
};

const PORES =
  '<defs><pattern id="pores" width="9" height="9" patternUnits="userSpaceOnUse">' +
  '<rect width="9" height="9" fill="#585D62"/><circle cx="2" cy="3" r="1.15" fill="#3A3E42"/>' +
  '<circle cx="6.6" cy="6.4" r=".85" fill="#41454A"/><circle cx="5.2" cy="1.4" r=".5" fill="#6E7378"/>' +
  '<circle cx="1.2" cy="7.6" r=".6" fill="#44484D"/></pattern></defs>';

const BLINK =
  "<style>.pupil{transform-box:fill-box;transform-origin:center;animation:b 3.6s infinite}" +
  "@keyframes b{0%,92%,100%{transform:scaleY(1)}95%{transform:scaleY(.1)}}" +
  "@media (prefers-reduced-motion:reduce){.pupil{animation:none}}</style>";

/** 돌하르방: 벙거지 모자, 툭 튀어나온 눈, 긴 코, 배 위에 얹은 두 손. */
export function hareubang(cls = "har") {
  return (
    `<svg class="${cls}" viewBox="0 0 120 200" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="돌하르방">` +
    BLINK + PORES +
    '<path d="M29 50 Q28 9 60 8 Q92 9 91 50 Z" fill="url(#pores)" stroke="#2B2E31" stroke-width="2"/>' +
    '<rect x="22" y="45" width="76" height="11" rx="5.5" fill="url(#pores)" stroke="#2B2E31" stroke-width="2"/>' +
    '<path d="M28 55 Q22 122 30 196 L90 196 Q98 122 92 55 Z" fill="url(#pores)" stroke="#2B2E31" stroke-width="2"/>' +
    '<circle cx="44" cy="76" r="11" fill="#6A6F74" stroke="#2B2E31" stroke-width="2.2"/>' +
    '<circle cx="76" cy="76" r="11" fill="#6A6F74" stroke="#2B2E31" stroke-width="2.2"/>' +
    '<circle class="pupil" cx="44" cy="77" r="4.4" fill="#25282B"/>' +
    '<circle class="pupil" cx="76" cy="77" r="4.4" fill="#25282B"/>' +
    '<path d="M60 74 Q51 100 53 113 Q60 120 67 113 Q69 100 60 74 Z" fill="#62676C" stroke="#2B2E31" stroke-width="1.8"/>' +
    '<path d="M47 128 Q60 135 73 128" stroke="#2B2E31" stroke-width="3" fill="none" stroke-linecap="round"/>' +
    '<rect x="33" y="146" width="36" height="12" rx="6" fill="#63686D" stroke="#2B2E31" stroke-width="1.8"/>' +
    '<rect x="51" y="165" width="36" height="12" rx="6" fill="#63686D" stroke="#2B2E31" stroke-width="1.8"/>' +
    "</svg>"
  );
}

export function gyul(cls = "gyul") {
  return (
    `<svg class="${cls}" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">` +
    '<circle cx="20" cy="22" r="15" fill="#F0892B"/><circle cx="15" cy="17" r="4" fill="#F8B06A" opacity=".7"/>' +
    '<circle cx="12" cy="25" r=".8" fill="#D9741A"/><circle cx="24" cy="29" r=".8" fill="#D9741A"/>' +
    '<circle cx="27" cy="19" r=".8" fill="#D9741A"/>' +
    '<path d="M20 8 Q27 2 33 6 Q27 12 20 8Z" fill="#2F7A4D"/><path d="M20 7.5v4" stroke="#1E5636" stroke-width="1.6"/></svg>'
  );
}

/** 시작 화면 그림: 귤빛 해, 한라산, 바다, 돌하르방, 귤. */
export function heroScene() {
  const har = hareubang("har").replace('<svg class="har" viewBox', '<svg class="har" x="128" y="58" width="108" height="180" viewBox');
  const g1 = gyul().replace('<svg class="gyul" viewBox', '<svg x="238" y="206" width="34" height="34" viewBox');
  const g2 = gyul().replace('<svg class="gyul" viewBox', '<svg x="268" y="214" width="26" height="26" viewBox');
  return (
    '<svg viewBox="0 0 360 250" xmlns="http://www.w3.org/2000/svg">' +
    '<circle cx="262" cy="70" r="46" fill="#F0892B" opacity=".92"/>' +
    '<path d="M0 170 Q70 120 130 128 Q180 70 225 96 Q290 128 360 150 L360 250 L0 250Z" fill="#7FB08A"/>' +
    '<path d="M0 186 Q90 150 170 160 Q260 168 360 170 L360 250 L0 250Z" fill="#2F7A4D"/>' +
    '<path d="M0 214 Q90 204 180 212 Q270 220 360 210 L360 250 L0 250Z" fill="#5E9BCF"/>' +
    '<path d="M0 232 Q90 224 180 230 Q270 238 360 230 L360 250 L0 250Z" fill="#2C6EA6"/>' +
    har + g1 + g2 + "</svg>"
  );
}

/** 감귤 모자를 쓴 꼬마 돌하르방 얼굴(하르방 버튼·대화창 얼굴). */
export function harGyul() {
  return (
    '<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="감귤 모자를 쓴 돌하르방">' +
    BLINK +
    '<defs><pattern id="sp" width="8" height="8" patternUnits="userSpaceOnUse">' +
    '<rect width="8" height="8" fill="#80868B"/><circle cx="2" cy="2.6" r="1" fill="#5F656A"/>' +
    '<circle cx="6" cy="6" r=".75" fill="#666C71"/><circle cx="5" cy="1.2" r=".45" fill="#9AA0A5"/></pattern></defs>' +
    '<path d="M22 46 Q20 92 50 93 Q80 92 78 46 Z" fill="url(#sp)" stroke="#2B2E31" stroke-width="2.4"/>' +
    '<path d="M14 49 Q13 14 50 12 Q87 14 86 49 Q50 58 14 49Z" fill="#F0892B" stroke="#B85E12" stroke-width="2.2"/>' +
    '<ellipse cx="34" cy="26" rx="9" ry="5" fill="#FBC58A" opacity=".85" transform="rotate(-25 34 26)"/>' +
    '<circle cx="28" cy="40" r="1.1" fill="#D06E16"/><circle cx="44" cy="44" r="1.1" fill="#D06E16"/>' +
    '<circle cx="62" cy="38" r="1.1" fill="#D06E16"/><circle cx="74" cy="45" r="1.1" fill="#D06E16"/><circle cx="54" cy="25" r="1.1" fill="#D06E16"/>' +
    '<path d="M50 13 L50 6" stroke="#5B3A1A" stroke-width="2.6" stroke-linecap="round"/>' +
    '<path d="M51 8 Q62 -1 74 5 Q63 14 51 8Z" fill="#3E9B5F" stroke="#1E5636" stroke-width="1.4"/>' +
    '<circle cx="37" cy="62" r="8" fill="#F4F2EE" stroke="#2B2E31" stroke-width="2"/>' +
    '<circle cx="63" cy="62" r="8" fill="#F4F2EE" stroke="#2B2E31" stroke-width="2"/>' +
    '<g class="pupil"><circle cx="38" cy="63" r="4.6" fill="#25282B"/><circle cx="39.6" cy="61.2" r="1.5" fill="#fff"/></g>' +
    '<g class="pupil"><circle cx="62" cy="63" r="4.6" fill="#25282B"/><circle cx="63.6" cy="61.2" r="1.5" fill="#fff"/></g>' +
    '<ellipse cx="28" cy="76" rx="6" ry="3.6" fill="#F5967A" opacity=".75"/>' +
    '<ellipse cx="72" cy="76" rx="6" ry="3.6" fill="#F5967A" opacity=".75"/>' +
    '<path d="M50 62 Q45 75 46.5 80 Q50 83.5 53.5 80 Q55 75 50 62Z" fill="#6A7075" stroke="#2B2E31" stroke-width="1.6"/>' +
    '<path d="M43 86 Q50 91 57 86" stroke="#2B2E31" stroke-width="2.4" fill="none" stroke-linecap="round"/>' +
    "</svg>"
  );
}

/**
 * 대화창·하르방 버튼 캐릭터: 패널 그림과 같은 돌하르방(벙거지 모자·툭 튀어나온 눈·긴 코·미소)을
 * 작은 원 안에서 잘 보이게 다듬었다. 밝은 현무암 색, 흰자위가 있는 눈, 모자 위 꼬마 감귤,
 * 아래가 둥근 몸통. 원 가운데에 오도록 그림 자체를 가운데 맞춤(가로 18~82, 세로 6~94).
 */
export function harMascot() {
  return (
    '<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="감귤 장식을 단 돌하르방">' +
    BLINK +
    '<defs><pattern id="mp" width="8" height="8" patternUnits="userSpaceOnUse">' +
    '<rect width="8" height="8" fill="#A9AFB4"/><circle cx="2" cy="2.6" r="1" fill="#8C9298"/>' +
    '<circle cx="6" cy="6" r=".75" fill="#939990"/><circle cx="5.2" cy="1.2" r=".45" fill="#C4C9CD"/></pattern></defs>' +
    // 둥근 몸통(아래 모서리를 둥글게)
    '<path d="M27 46 Q24 70 28 84 Q31 94 50 94 Q69 94 72 84 Q76 70 73 46 Z" fill="url(#mp)" stroke="#3A3F44" stroke-width="2.2" stroke-linejoin="round"/>' +
    // 벙거지 모자: 둥근 꼭대기 + 챙
    '<path d="M29 43 Q28 14 50 13 Q72 14 71 43 Z" fill="url(#mp)" stroke="#3A3F44" stroke-width="2.2"/>' +
    '<rect x="22" y="39" width="56" height="9" rx="4.5" fill="#9FA5AA" stroke="#3A3F44" stroke-width="2.2"/>' +
    // 모자 위 꼬마 감귤
    '<circle cx="63" cy="14" r="7.2" fill="#F0892B" stroke="#B85E12" stroke-width="1.4"/>' +
    '<ellipse cx="60.5" cy="11.6" rx="2.4" ry="1.5" fill="#FBC58A" transform="rotate(-25 60.5 11.6)"/>' +
    '<path d="M63 7.2 Q69 1.5 75 5 Q69 10 63 7.2Z" fill="#3E9B5F" stroke="#1E5636" stroke-width="1"/>' +
    // 흰자위가 있는 눈
    '<circle cx="39" cy="58" r="7.6" fill="#FFFFFF" stroke="#3A3F44" stroke-width="2"/>' +
    '<circle cx="61" cy="58" r="7.6" fill="#FFFFFF" stroke="#3A3F44" stroke-width="2"/>' +
    '<g class="pupil"><circle cx="40" cy="59" r="3.9" fill="#25282B"/><circle cx="41.3" cy="57.6" r="1.2" fill="#fff"/></g>' +
    '<g class="pupil"><circle cx="60" cy="59" r="3.9" fill="#25282B"/><circle cx="61.3" cy="57.6" r="1.2" fill="#fff"/></g>' +
    // 볼, 긴 코, 미소
    '<ellipse cx="31" cy="72" rx="4.6" ry="2.8" fill="#F5967A" opacity=".7"/>' +
    '<ellipse cx="69" cy="72" rx="4.6" ry="2.8" fill="#F5967A" opacity=".7"/>' +
    '<path d="M50 57 Q44.5 71 46 77 Q50 80.5 54 77 Q55.5 71 50 57Z" fill="#8E949A" stroke="#3A3F44" stroke-width="1.6"/>' +
    '<path d="M42 84 Q50 89.5 58 84" stroke="#3A3F44" stroke-width="2.4" fill="none" stroke-linecap="round"/>' +
    "</svg>"
  );
}

const r1 = (n: number) => +n.toFixed(1);

/** 땅에 놓인 한라봉(꼭지가 볼록한 귤). (cx, base)는 밑동, s는 크기 배율 */
function hallabong(cx: number, base: number, s: number) {
  const bodyCy = base - 10 * s, knobCy = base - 20 * s;
  return (
    `<ellipse cx="${cx}" cy="${r1(base)}" rx="${r1(12 * s)}" ry="${r1(2.4 * s)}" fill="#000" opacity=".14"/>` +
    `<ellipse cx="${cx}" cy="${r1(bodyCy)}" rx="${r1(12 * s)}" ry="${r1(10 * s)}" fill="#F0892B"/>` +
    `<ellipse cx="${cx}" cy="${r1(knobCy)}" rx="${r1(5 * s)}" ry="${r1(3.6 * s)}" fill="#F0892B"/>` +
    `<ellipse cx="${r1(cx - 4.5 * s)}" cy="${r1(bodyCy - 3 * s)}" rx="${r1(3 * s)}" ry="${r1(1.8 * s)}" fill="#F8B06A" opacity=".8"/>` +
    `<path d="M${r1(cx - 5 * s)} ${r1(knobCy + s)} Q${r1(cx - 11 * s)} ${r1(knobCy - 4 * s)} ${r1(cx - 14 * s)} ${r1(knobCy)} Q${r1(cx - 10 * s)} ${r1(knobCy + 3 * s)} ${r1(cx - 5 * s)} ${r1(knobCy + s)}Z" fill="#2F7A4D"/>`
  );
}

/** 땅에 선 돌하르방. (cx, feet)는 발 자리, h는 키. 발밑 그림자로 땅에 붙어 보이게 */
function harbangAt(cx: number, feet: number, h: number) {
  const w = h * 0.6; // 하르방 그림 비율 120:200, 몸통 바닥은 196/200
  const har = hareubang("har").replace('<svg class="har" viewBox',
    `<svg class="har" x="${r1(cx - w / 2)}" y="${r1(feet - h * 0.98)}" width="${r1(w)}" height="${r1(h)}" viewBox`);
  return `<ellipse cx="${cx}" cy="${r1(feet)}" rx="${r1(w * 0.42)}" ry="${r1(h * 0.045)}" fill="#000" opacity=".18"/>` + har;
}

/** 입체 글자 'JEJU': 같은 글자를 아래오른쪽으로 겹쳐 주황 두께를 만들고 맨 위에 주황 테두리의 흰 글자. (cx, y)는 가운데·글자 바닥 */
function jejuTitle(cx: number, y: number, size = 34) {
  // <img> 안의 SVG는 웹 글꼴을 못 불러오므로 시스템 굵은 글꼴을 쓴다
  const t = (dx: number, dy: number, fill: string, extra = "") =>
    `<text x="${r1(cx + dx)}" y="${r1(y + dy)}" text-anchor="middle" font-family="'Arial Black','Segoe UI Black',Impact,'Helvetica Neue',Arial,sans-serif" ` +
    `font-weight="900" font-size="${size}" letter-spacing="3" fill="${fill}"${extra}>JEJU</text>`;
  let depth = t(4, 5, "#000", ' opacity=".16"'); // 땅에 지는 그림자
  for (let i = 4; i >= 1; i--) depth += t(i * 0.8, i * 0.9, i > 2 ? "#B85E12" : "#D9741A");
  return depth + t(0, 0, "#FFFFFF", ' stroke="#F0892B" stroke-width="1.6" paint-order="stroke"');
}

// ---------- 시작 그림의 하늘: 제주의 실제 해·달 ----------
const JEJU_LAT = 33.4, JEJU_LON = 126.5;
const RAD = Math.PI / 180;

/** 제주(한국) 시각: 소수 시간(13.5 = 오후 1시 30분)과 그해 몇째 날. 보는 사람 컴퓨터 시간대와 상관없다 */
export function jejuTime(d = new Date()): { hour: number; doy: number } {
  const k = new Date(d.getTime() + 9 * 3600_000); // 한국은 서머타임이 없어 UTC+9 고정
  const doy = Math.floor((Date.UTC(k.getUTCFullYear(), k.getUTCMonth(), k.getUTCDate()) - Date.UTC(k.getUTCFullYear(), 0, 1)) / 86400_000) + 1;
  return { hour: k.getUTCHours() + k.getUTCMinutes() / 60, doy };
}

/** 그날 제주의 해 뜨는·지는 시각(한국 시각, 소수 시간). 태양 적위·균시차 근사식(몇 분 안쪽 오차) */
export function sunTimes(doy: number): { rise: number; set: number } {
  const decl = -23.44 * Math.cos((2 * Math.PI * (doy + 10)) / 365) * RAD;
  const B = (2 * Math.PI * (doy - 81)) / 364;
  const eot = 9.87 * Math.sin(2 * B) - 7.53 * Math.cos(B) - 1.5 * Math.sin(B); // 분
  const noon = 12 + (135 - JEJU_LON) / 15 - eot / 60; // 한국 표준시 기준 경도 135°
  // 해 윗가장자리가 수평선에 닿는 때(-0.83°)
  const cosH = (Math.sin(-0.83 * RAD) - Math.sin(JEJU_LAT * RAD) * Math.sin(decl)) / (Math.cos(JEJU_LAT * RAD) * Math.cos(decl));
  const half = Math.acos(Math.max(-1, Math.min(1, cosH))) / RAD / 15;
  return { rise: noon - half, set: noon + half };
}

/** 달의 위상 0~1(0 삭, 0.25 상현, 0.5 보름, 0.75 하현). 2000-01-06 18:14 UTC 삭 기준 평균 삭망월 */
export function moonPhase(d: Date): number {
  const days = (d.getTime() - Date.UTC(2000, 0, 6, 18, 14)) / 86400_000;
  return (((days / 29.530588853) % 1) + 1) % 1;
}

type Sky = { sky: string; sea: string; dim: number; sun: string; dark: boolean; label: string };

/** 해 뜨고 지는 시각에 맞춘 하늘: 밤·해 뜰 무렵·낮·노을·해 진 저녁 */
function skyAt(h: number, rise: number, set: number): Sky {
  if (h < rise - 0.75 || h > set + 0.75) return { sky: "#1E2B47", sea: "#38557A", dim: 0.55, sun: "", dark: true, label: "밤" };
  if (h < rise + 0.75) return { sky: "#F6D4C2", sea: "#9CC3DD", dim: 0.9, sun: "#F2884A", dark: false, label: "해 뜰 무렵" };
  if (h < set - 1.25) return { sky: "#FBF3E8", sea: "#A9D2E8", dim: 1, sun: "#F6B36B", dark: false, label: "낮" };
  if (h < set) return { sky: "#F7C89E", sea: "#9CC3DD", dim: 0.88, sun: "#EE7A3A", dark: false, label: "노을 지는 저녁" };
  return { sky: "#5B5A7E", sea: "#5F7899", dim: 0.7, sun: "", dark: true, label: "해 진 저녁" };
}

/**
 * 하늘을 가로지르는 활 모양 길. 그림은 오른쪽이 동쪽(성산일출봉), 왼쪽이 서쪽이라
 * t=0 오른쪽(동쪽) 수평선에서 떠서 0.5 가운데 가장 높이, 1 왼쪽(서쪽) 수평선으로 진다.
 */
function arc(t: number): [number, number] {
  return [r1(370 - 340 * t), r1(80 - 56 * Math.sin(Math.PI * t))];
}

/** 위상에 맞는 달 모양(밝은 쪽: 차오를 때 오른쪽, 기울 때 왼쪽). 어두운 쪽은 옅게 */
function moonShape(x: number, y: number, r: number, p: number, fill: string) {
  const k = Math.cos(2 * Math.PI * p); // 1 삭, -1 보름
  const rx = r1(Math.abs(k) * r);
  const lit = p < 0.5
    ? `M${x} ${r1(y - r)} A${r} ${r} 0 0 1 ${x} ${r1(y + r)} A${rx} ${r} 0 0 ${k > 0 ? 0 : 1} ${x} ${r1(y - r)}Z`
    : `M${x} ${r1(y - r)} A${r} ${r} 0 0 0 ${x} ${r1(y + r)} A${rx} ${r} 0 0 ${k > 0 ? 1 : 0} ${x} ${r1(y - r)}Z`;
  return `<circle cx="${x}" cy="${y}" r="${r}" fill="${fill}" opacity=".16"/><path d="${lit}" fill="${fill}"/>`;
}

/** 밤에 하르방을 비추는 불빛: 뒤로 번지는 따뜻한 빛 + 발밑 빛 웅덩이(흐림 필터, 그라데이션 아님) */
function harbangGlow(cx: number, feet: number, h: number) {
  return (
    `<ellipse cx="${cx}" cy="${r1(feet - h * 0.5)}" rx="${r1(h * 0.34)}" ry="${r1(h * 0.48)}" fill="#FFD58A" opacity=".32" filter="url(#glow)"/>` +
    `<ellipse cx="${cx}" cy="${r1(feet)}" rx="${r1(h * 0.3)}" ry="${r1(h * 0.06)}" fill="#FFE2A8" opacity=".4" filter="url(#glow)"/>`
  );
}

/** 그 시각 하늘의 이름(그림 설명 글에 쓴다) */
export function heroLabel(at?: Date): string {
  if (!at) return "낮";
  const { hour, doy } = jejuTime(at);
  const { rise, set } = sunTimes(doy);
  return skyAt(hour, rise, set).label;
}

/**
 * 패널 시작 그림(가로로 긴 띠): 바다 위 제주도와 한라산, 산 앞 섬 위에 입체 글자 JEJU,
 * 섬 왼쪽에 한라봉 둘, 오른쪽에 돌하르방 둘(각각 크기 다르게, 뒤가 작게).
 * at(지금 시각)을 주면 제주의 실제 해·달을 그린다: 그날 해 뜨는 시각에 오른쪽(동쪽)에서 떠 가운데를 지나
 * 해 지는 시각에 왼쪽(서쪽)으로 지고, 달은 오늘 위상 모양으로 뜨는 동안(남중 ±6시간쯤)만 같은 길을 지난다.
 * 어두울 때는 섬이 어두워지고 하르방은 불빛을 받아 밝게 보인다.
 * at 이 없으면(서버 그림) 여름 낮. 양옆이 잘려도 섬이 가운데에 남게 그렸다.
 * 디자인 원칙(web/DESIGN.md)에 맞춰 그라데이션 없이 단색만 쓴다.
 */
export function heroBanner(at?: Date) {
  const { hour: h, doy } = at ? jejuTime(at) : { hour: 12.5, doy: 172 };
  const { rise, set } = sunTimes(doy);
  const c = skyAt(h, rise, set);
  let light = "";
  if (c.dark) {
    light += '<g fill="#F4EBD0">' +
      [[40, 20], [96, 44], [150, 16], [232, 30], [286, 14], [352, 40], [380, 18], [120, 64], [262, 58]]
        .map(([sx, sy], i) => `<circle cx="${sx}" cy="${sy}" r="${i % 3 ? 0.9 : 1.4}"/>`).join("") + "</g>";
  }
  if (at) {
    // 달: 남중 시각은 위상에 따라 매일 약 50분씩 늦어진다(삭은 낮 12시 반, 보름은 자정 반 무렵)
    const p = moonPhase(at);
    const transit = (12 + 24 * p + (135 - JEJU_LON) / 15) % 24;
    const off = ((h - transit + 36) % 24) - 12; // 남중에서 몇 시간 지났나(-12~12)
    if (Math.abs(off) <= 6.2 && p > 0.03 && p < 0.97) {
      const [x, y] = arc((off + 6.2) / 12.4);
      light += `<g opacity="${c.dark ? 1 : 0.55}">${moonShape(x, y, 12, p, "#F4EBD0")}</g>`;
    }
  }
  if (h >= rise && h <= set) {
    const [x, y] = arc((h - rise) / (set - rise));
    light += `<circle cx="${x}" cy="${y}" r="16" fill="${c.sun}"/>`;
  }
  // 어두운 시간에는 바다·섬을 같은 비율로 어둡게(글자 JEJU와 불빛 받은 하르방은 밝게)
  const defs =
    (c.dim < 1
      ? `<filter id="dim"><feComponentTransfer><feFuncR type="linear" slope="${c.dim}"/><feFuncG type="linear" slope="${c.dim}"/>` +
        `<feFuncB type="linear" slope="${Math.min(1, c.dim + 0.12)}"/></feComponentTransfer></filter>`
      : "") +
    (c.dark
      ? '<filter id="glow" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="2.6"/></filter>' +
        // 불빛 받은 하르방: 섬보다 덜 어둡게만(너무 밝으면 떠 보인다)
        '<filter id="lit"><feComponentTransfer><feFuncR type="linear" slope=".8"/><feFuncG type="linear" slope=".78"/><feFuncB type="linear" slope=".74"/></feComponentTransfer></filter>'
      : "");
  const harbangs =
    harbangAt(330, 112, 34) +
    harbangAt(298, 124, 50);
  return (
    '<svg viewBox="0 0 400 150" preserveAspectRatio="xMidYMax slice" xmlns="http://www.w3.org/2000/svg">' +
    (defs ? `<defs>${defs}</defs>` : "") +
    // 하늘·별·달·해. 해와 달은 바다 뒤로 지도록 바다보다 먼저 그린다
    `<rect width="400" height="150" fill="${c.sky}"/>` +
    light +
    `<g${c.dim < 1 ? ' filter="url(#dim)"' : ""}>` +
    // 바다와 잔물결
    `<rect y="78" width="400" height="72" fill="${c.sea}"/>` +
    '<path d="M36 92 q8 -4 16 0 M140 86 q8 -4 16 0 M52 142 q8 -4 16 0 M318 144 q8 -4 16 0" stroke="#7FB6D6" stroke-width="2" fill="none" stroke-linecap="round"/>' +
    // 제주도(동서로 긴 섬) + 바닷가 띠
    '<path d="M28 118 Q40 100 92 97 Q150 88 200 90 Q262 88 322 95 Q364 100 374 112 Q370 128 328 132 Q262 140 200 138 Q128 140 70 134 Q32 130 28 118Z" fill="#E9DDC4"/>' +
    '<path d="M36 116 Q48 103 94 101 Q150 93 200 95 Q260 93 318 99 Q356 103 365 113 Q360 125 326 128 Q260 135 200 133 Q130 135 72 129 Q40 126 36 116Z" fill="#7FB08A"/>' +
    // 가운데 한라산(백록담), 동쪽 끝 성산일출봉·우도
    '<path d="M118 112 Q190 62 262 112 Z" fill="#5E9B70"/>' +
    '<path d="M176 80 Q190 70 204 80 Q190 84 176 80Z" fill="#4C8A5F"/>' +
    '<path d="M350 110 Q358 96 370 106 Z" fill="#4C8A5F"/>' +
    '<ellipse cx="388" cy="106" rx="7" ry="3.4" fill="#7FB08A"/>' +
    // 왼쪽 한라봉 둘(뒤가 작게)
    hallabong(102, 113, 0.62) +
    hallabong(76, 122, 0.85) +
    // 낮에는 하르방도 같은 빛으로(밤에는 아래에서 따로 불빛과 함께 그린다)
    (c.dark ? "" : harbangs) +
    "</g>" +
    (c.dark ? harbangGlow(330, 112, 34) + harbangGlow(298, 124, 50) + `<g filter="url(#lit)">${harbangs}</g>` : "") +
    // 산 앞 섬 위 JEJU
    jejuTitle(190, 124) +
    "</svg>"
  );
}

// 자주 쓰는 그림은 한 번만 만든다
export const ART = {
  hareubang: dataUri(hareubang()),
  gyul: dataUri(gyul("g")),
  hero: dataUri(heroScene()),
  harGyul: dataUri(harGyul()),
  harFace: dataUri(harMascot()),
};
