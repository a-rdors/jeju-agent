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

/**
 * 패널 시작 그림(가로로 긴 띠). 양옆이 잘리지 않게 하늘·산·바다가 띠 끝까지 이어진다.
 * 높이를 줄여도 그림 전체가 띠 모양 그대로 줄어든다.
 */
export function heroBanner() {
  const har = hareubang("har").replace('<svg class="har" viewBox', '<svg class="har" x="166" y="20" width="64" height="107" viewBox');
  const g1 = gyul().replace('<svg class="gyul" viewBox', '<svg x="228" y="104" width="24" height="24" viewBox');
  const g2 = gyul().replace('<svg class="gyul" viewBox', '<svg x="250" y="110" width="18" height="18" viewBox');
  return (
    '<svg viewBox="0 0 400 150" preserveAspectRatio="xMidYMax slice" xmlns="http://www.w3.org/2000/svg">' +
    '<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FBF3E8"/>' +
    '<stop offset="1" stop-color="#F6E7D6"/></linearGradient></defs>' +
    '<rect width="400" height="150" fill="url(#sky)"/>' +
    '<circle cx="300" cy="48" r="30" fill="#F0892B" opacity=".92"/>' +
    '<path d="M0 92 Q60 66 120 72 Q180 30 240 54 Q320 84 400 80 L400 150 L0 150Z" fill="#7FB08A"/>' +
    '<path d="M0 106 Q100 84 190 94 Q290 102 400 96 L400 150 L0 150Z" fill="#2F7A4D"/>' +
    '<path d="M0 124 Q100 116 200 122 Q300 128 400 120 L400 150 L0 150Z" fill="#5E9BCF"/>' +
    '<path d="M0 138 Q100 132 200 137 Q300 143 400 136 L400 150 L0 150Z" fill="#2C6EA6"/>' +
    har + g1 + g2 + "</svg>"
  );
}

// 자주 쓰는 그림은 한 번만 만든다
export const ART = {
  hareubang: dataUri(hareubang()),
  gyul: dataUri(gyul("g")),
  hero: dataUri(heroScene()),
  harGyul: dataUri(harGyul()),
  harFace: dataUri(harMascot()),
  heroBanner: dataUri(heroBanner()),
};
