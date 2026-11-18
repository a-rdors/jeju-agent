"""화면 꾸미기 조각: 색·글꼴(CSS), 하르방·귤 그림(SVG), 결과 카드 HTML.

색 체계
- 귤색: 주 버튼, 식당, 강조
- 감귤잎 초록: '갈 만해요', 코스
- 제주 바다 파랑: '동행인 도움이 있으면 갈 만해요' (귤색과 헷갈리지 않게 주황 대신 파랑)
- 현무암 회색: '확인이 더 필요해요', 상단 바, 하르방
"""
import base64
from html import escape

VERDICT = {  # tools.verdict_color -> (색 이름, 아이콘)
    "green": ("leaf", "check"),
    "orange": ("sea", "people"),
    "gray": ("stone", "question"),
}
VERDICT_HEX = {"green": "#2F7A4D", "orange": "#2C6EA6", "gray": "#6B7075"}

PRETENDARD = "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css"

# 화면 틀: 지도는 화면 전체, 위에 떠 있는 상단 바 · 오른쪽 대시보드 · 오른쪽 아래 하르방 버튼과 대화창.
CSS = """<style>
@import url('""" + PRETENDARD + """');
:root{
  --gyul:#F0892B; --gyul-hover:#E07A1C; --gyul-soft:#FDE9D6; --gyul-text:#9C4A07;
  --leaf:#2F7A4D; --leaf-deep:#1E5636; --leaf-soft:#E3F1E7;
  --sea:#2C6EA6; --sea-soft:#E2EDF7;
  --basalt:#2E3135; --stone:#E8E9E5; --stone-2:#D7D9D3; --stone-text:#5B6166;
  --paper:#F5F5F1; --card:#FFFFFF; --ink:#1D2124; --muted:#565D63; --red:#B83227;
  --font:"Pretendard Variable",Pretendard,-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Malgun Gothic",sans-serif;
  --shadow:0 10px 30px rgba(20,24,28,.18),0 2px 6px rgba(20,24,28,.10);
  --dash-w:420px; --dash-r:16px; --top-max:calc(100vw - 484px);
}
html,body,.stApp,button,input,textarea,select{font-family:var(--font)!important}
.stApp [data-testid="stMarkdownContainer"],.stApp p,.stApp label,.stApp li{font-family:var(--font)}
header[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"],[data-testid="stStatusWidget"]{display:none!important}
.stApp{background:#DCE8EE}
.block-container{max-width:none!important;padding:0!important}
h1,h2,h3,.brand b,.verdict .vl,.place-name,.sect,.hello h1,.chat-head b{font-family:var(--font)!important;font-weight:800!important;letter-spacing:-.01em}

/* 지도 자리(카카오맵 키가 없을 때 기본 지도) */
.st-key-mapbox{position:fixed!important;inset:0;z-index:0}
.st-key-mapbox [data-testid="stElementContainer"],.st-key-mapbox [data-testid="stDeckGlJsonChart"]{height:100dvh!important}

/* 현무암 질감: 숭숭 뚫린 구멍 */
.basalt,.st-key-topbar,.st-key-chathead{
  background-color:var(--basalt);
  background-image:
    radial-gradient(circle at 30% 40%, rgba(0,0,0,.35) 0 2.2px, transparent 3px),
    radial-gradient(circle at 70% 70%, rgba(255,255,255,.07) 0 1.6px, transparent 2.4px),
    radial-gradient(circle at 50% 20%, rgba(0,0,0,.25) 0 1.3px, transparent 2px);
  background-size:26px 22px, 19px 23px, 13px 15px;
}

/* 상단 바: 지도 위 왼쪽 위에 떠 있다 */
.st-key-topbar{position:fixed!important;top:16px;left:16px;z-index:30;width:auto!important;max-width:var(--top-max);
  border-radius:20px;padding:8px 10px 8px 14px;min-height:56px;box-shadow:var(--shadow)}
.st-key-topbar p,.st-key-topbar label,.st-key-topbar span{color:#F3F1EC!important}
.st-key-topbar [data-testid="stBaseButton-tertiary"]{color:#F3F1EC!important;border:1px solid rgba(255,255,255,.25)!important;border-radius:12px;padding:4px 10px;min-height:36px}
.st-key-topbar [data-testid="stBaseButton-tertiary"]:hover{background:rgba(255,255,255,.1)!important}
.st-key-topbar [data-testid="stCheckbox"] label > div:first-child{background:rgba(255,255,255,.35)!important}
.brand{display:flex;align-items:center;gap:10px;color:#fff;white-space:nowrap}
.brand b{font-size:1.25rem;color:#fff}
.brand small{display:block;font-size:.76rem;color:#C9CCC6;margin-top:-1px}
.chips{display:flex;flex-wrap:nowrap;gap:6px;overflow:hidden}
.chip{display:inline-flex;align-items:center;gap:5px;padding:4px 11px;border-radius:999px;font-size:.86rem;font-weight:600;white-space:nowrap;
      background:rgba(255,255,255,.12);color:#F3F1EC;border:1px solid rgba(255,255,255,.2)}
.chip.gyul{background:var(--gyul);color:#2A1606;border-color:var(--gyul)}

/* 버튼 */
[data-testid="stBaseButton-primary"]{background:var(--gyul)!important;border:2px solid var(--gyul)!important;color:#2A1606!important;
  font-weight:700!important;border-radius:14px!important;min-height:46px}
[data-testid="stBaseButton-primary"]:hover{background:var(--gyul-hover)!important;border-color:var(--gyul-hover)!important}
[data-testid="stBaseButton-primary"] p,[data-testid="stBaseButton-primary"] span{color:#2A1606!important;font-weight:700}
[data-testid="stBaseButton-secondary"]{border-radius:14px!important;border:2px solid var(--stone-2)!important;background:var(--card)!important;min-height:42px}
[data-testid="stBaseButton-secondary"]:hover{border-color:var(--leaf)!important;color:var(--leaf-deep)!important}
.stLinkButton a{border-radius:14px!important;min-height:42px}

/* 오른쪽 대시보드 */
.st-key-dash{position:fixed!important;top:16px;right:var(--dash-r);bottom:108px;width:var(--dash-w)!important;z-index:20;
  background:rgba(255,255,255,.97);border:1px solid var(--stone-2);border-radius:24px;padding:18px 18px 22px;
  overflow-y:auto!important;overscroll-behavior:contain;box-shadow:var(--shadow);
  display:flex!important;flex-direction:column;flex-wrap:nowrap!important;transition:right .25s ease}
.st-key-dash > *{flex-shrink:0}
.dash-head{display:flex;align-items:baseline;justify-content:space-between;gap:8px}
.dash-head b{font-size:.82rem;font-weight:700;color:var(--gyul-text);background:var(--gyul-soft);padding:3px 10px;border-radius:999px}
.dash-head span{font-size:.85rem;color:var(--muted)}

/* 지도 위 '찾는 중' 표시 */
.searching{position:fixed;top:88px;left:16px;z-index:25;display:flex;align-items:center;gap:10px;background:#fff;border-radius:999px;
  padding:8px 16px 8px 10px;box-shadow:var(--shadow);font-weight:700;color:var(--ink)}
.searching img{width:28px;height:28px;animation:spin 1.6s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}

/* 하르방 버튼(오른쪽 아래) */
.st-key-chatfab{position:fixed!important;right:22px;bottom:20px;z-index:50;width:auto!important}
.st-key-chatfab button{width:76px;height:76px;min-height:76px;border-radius:50%!important;padding:0!important;
  border:3px solid var(--gyul)!important;background:#FFF8EF var(--fab-img) center bottom/92% no-repeat!important;
  box-shadow:0 8px 22px rgba(160,80,10,.35),0 2px 6px rgba(0,0,0,.18);transition:transform .15s ease}
.st-key-chatfab button:hover{transform:translateY(-2px) scale(1.05)}
.st-key-chatfab button:focus-visible{outline:3px solid var(--ink)!important;outline-offset:3px}
.st-key-chatfab button p{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.fab-hint{position:fixed;right:110px;bottom:38px;z-index:49;background:#fff;color:var(--ink);font-weight:700;font-size:.95rem;
  border-radius:16px 16px 4px 16px;padding:10px 14px;box-shadow:var(--shadow);animation:float 2.6s ease-in-out infinite}
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-4px)}}

/* 대화창 */
.st-key-chatwin{position:fixed!important;top:16px;right:16px;bottom:108px;width:380px!important;z-index:40;background:var(--card);
  border-radius:24px;box-shadow:var(--shadow);overflow:hidden;display:flex!important;flex-direction:column;flex-wrap:nowrap!important;
  gap:0!important;animation:pop .2s ease-out;transform-origin:bottom right}
@keyframes pop{from{opacity:0;transform:translateY(12px) scale(.97)}to{opacity:1;transform:none}}
.st-key-chathead{flex:0 0 auto;padding:10px 10px 10px 14px}
.st-key-chathead [data-testid="stBaseButton-tertiary"]{color:#F3F1EC!important;min-height:36px}
.chat-head{display:flex;align-items:center;gap:10px;color:#fff}
.chat-head b{font-size:1.05rem;color:#fff;display:block}
.chat-head small{color:#C9CCC6;font-size:.8rem}
.chat-head .avatar{background:#FFF3E3}
.st-key-chatwin > div:has(.st-key-chathead){flex:0 0 auto!important}
.st-key-chatwin > div:has(.st-key-chatlog){flex:1 1 0!important;min-height:0!important;display:flex;flex-direction:column}
.st-key-chatlog{flex:1 1 0!important;min-height:0;height:100%;overflow-y:auto!important;display:flex!important;flex-direction:column-reverse!important;
  padding:14px 12px 10px;background:var(--paper);overscroll-behavior:contain}
.st-key-chatlog > *,.st-key-chatlog [data-testid="stVerticalBlock"] > *,.st-key-chatlog [data-testid="stHorizontalBlock"] > *{flex-shrink:0}
.st-key-chatlog [class*="st-key-bot_"] > *:last-child{flex:1 1 0!important;min-width:0}
.st-key-chatwin [data-testid="stChatInput"]{border:2px solid var(--stone-2);border-radius:16px;margin:0}
.st-key-chatwin > .st-key-chat_text{padding:10px 12px 12px;flex:0 0 auto!important}
.msg-me{align-self:flex-end;max-width:85%;margin-left:auto;background:var(--gyul);color:#2A1606;font-weight:600;
  border-radius:18px 18px 4px 18px;padding:9px 13px;font-size:.98rem;line-height:1.45;word-break:keep-all}
[class*="st-key-botb_"]{background:#fff;border:1px solid var(--stone-2);border-radius:18px 18px 18px 4px;padding:10px 12px;min-width:0}
[class*="st-key-botb_"] [data-testid="stMarkdownContainer"]{margin-bottom:0!important}
[class*="st-key-botb_"] p:last-child{margin-bottom:0!important}
[class*="st-key-botb_"] p{margin:0 0 4px;font-size:.98rem;line-height:1.55;word-break:keep-all}
[class*="st-key-mplaces_"] button{min-height:32px!important;padding:2px 10px!important;border-radius:999px!important;border:1.5px solid #CFE3D5!important;background:var(--leaf-soft)!important}
[class*="st-key-mplaces_"] button p{font-size:.86rem;font-weight:700;color:var(--leaf-deep)}
.st-key-examples button,.st-key-askopts button{border-radius:999px!important;min-height:36px!important}
.st-key-examples button p{font-size:.9rem}
.typing{display:flex;gap:8px;align-items:flex-start}
.typing .bub{background:#fff;border:1px solid var(--stone-2);border-radius:18px 18px 18px 4px;padding:10px 14px}
.dots{display:inline-flex;gap:5px;padding:4px 0}
.dots i{width:8px;height:8px;border-radius:50%;background:var(--gyul);animation:dot 1.2s infinite ease-in-out}
.dots i:nth-child(2){animation-delay:.15s;background:#F3A35A} .dots i:nth-child(3){animation-delay:.3s;background:var(--leaf)}
@keyframes dot{0%,80%,100%{transform:translateY(0);opacity:.5}40%{transform:translateY(-5px);opacity:1}}
.typing .steps{position:relative;height:1.4em;min-width:210px;font-size:.88rem;color:var(--muted)}
.typing .steps span{position:absolute;inset:0;opacity:0;animation:step 6s infinite;white-space:nowrap}
.typing .steps span:nth-child(2){animation-delay:2s} .typing .steps span:nth-child(3){animation-delay:4s}
@keyframes step{0%{opacity:0;transform:translateY(4px)}6%,30%{opacity:1;transform:none}36%,100%{opacity:0}}
@media (prefers-reduced-motion:reduce){.dots i,.fab-hint,.searching img,.typing .steps span{animation:none}.typing .steps span:first-child{opacity:1}.st-key-chatwin{animation:none}}

/* 하르방 얼굴 */
.avatar{flex:0 0 40px;width:40px;height:40px;border-radius:50%;background:var(--gyul-soft);display:flex;align-items:flex-end;justify-content:center;overflow:hidden}
.avatar img{width:40px;height:40px;margin-bottom:-3px}
.trace{display:flex;flex-wrap:wrap;gap:5px;margin-top:2px}
.trace span{font-size:.76rem;color:var(--leaf-deep);background:var(--leaf-soft);border-radius:999px;padding:2px 8px}

/* 시작(대시보드 첫 화면) */
.hero-art{background:linear-gradient(180deg,#FBF3E8 0%,#F7EBDD 62%,#E9F1EA 100%);border-radius:20px;padding:10px 10px 0;display:flex;justify-content:center;overflow:hidden}
.hero-art img{width:100%;max-width:340px;height:auto;display:block}
.hello h1{font-size:1.65rem;line-height:1.25;margin:6px 0 4px}
.hello p{font-size:.98rem;color:var(--muted);margin:0}
.hello .eyebrow{display:inline-block;font-weight:700;color:var(--gyul-text);background:var(--gyul-soft);padding:3px 10px;border-radius:999px;font-size:.82rem}
.choice{display:flex;align-items:center;gap:12px}
.choice .ic{flex:0 0 44px;height:44px;border-radius:14px;display:flex;align-items:center;justify-content:center}
.choice .ic img{width:26px;height:26px}
.choice b{font-size:1.02rem;display:block}
.choice span{color:var(--muted);font-size:.86rem}
[class*="st-key-choice_"]{background:var(--card);border:2px solid var(--stone-2);border-radius:18px;padding:10px 12px}
[class*="st-key-choice_"]:hover{border-color:var(--gyul)}
[class*="st-key-choice_"] [data-testid="stBaseButton-primary"]{min-height:40px}
.tip-line{font-size:.85rem;color:var(--muted);background:var(--paper);border-radius:12px;padding:8px 10px}

/* 탭 */
[data-testid="stButtonGroup"] > div{flex-wrap:nowrap!important;overflow-x:auto}
[data-testid="stButtonGroup"] button{min-height:40px;border-radius:12px!important;font-weight:600;padding:0 10px!important;white-space:nowrap}

/* 판정 */
.verdict{display:flex;gap:12px;align-items:center;border-radius:18px;padding:14px 16px;color:#fff}
.verdict.leaf{background:var(--leaf)} .verdict.sea{background:var(--sea)} .verdict.stone{background:#5E6368}
.verdict .vi{flex:0 0 44px;height:44px;border-radius:50%;background:rgba(255,255,255,.18);display:flex;align-items:center;justify-content:center}
.verdict .vi img{width:26px;height:26px}
.verdict .vl{font-size:1.35rem;line-height:1.25}
.verdict .vr{font-size:.93rem;opacity:.95}
.place-name{font-size:1.55rem;line-height:1.25;margin:12px 0 2px;color:var(--ink)}
.place-where{color:var(--muted);font-size:.93rem}
.tiles{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:12px}
.tile{background:var(--paper);border:1px solid var(--stone-2);border-radius:14px;padding:9px 10px 8px;min-width:0}
.tile small{display:block;color:var(--muted);font-size:.78rem}
.tile b{display:block;font-size:.98rem;line-height:1.3;font-weight:700}
.tile.yes b{color:var(--leaf-deep)} .tile.no b{color:var(--stone-text)}
.notes{display:grid;gap:6px;margin:12px 0 4px;padding:0;list-style:none}
.notes li{display:flex;gap:8px;align-items:flex-start;font-size:.96rem}
.notes li i{flex:0 0 22px;height:22px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-style:normal;font-size:.8rem;font-weight:700;margin-top:2px}
.notes .good i{background:var(--leaf-soft);color:var(--leaf-deep)} .notes .warn i{background:#F8E1DE;color:var(--red)}
.weather{display:flex;gap:10px;align-items:flex-start;background:var(--sea-soft);border-radius:14px;padding:10px 12px;margin-top:10px;font-size:.92rem}
.weather b{color:var(--sea)}
.sect{font-size:1.1rem;margin:16px 0 8px;color:var(--ink)}
.checks{display:grid;gap:0;border:1px solid var(--stone-2);border-radius:14px;overflow:hidden}
.checks div{display:grid;grid-template-columns:6.5em minmax(0,1fr) auto;gap:8px;align-items:center;padding:9px 11px;border-top:1px solid var(--stone)}
.checks div:first-child{border-top:none}
.checks b{font-size:.92rem} .checks span{font-size:.9rem}
.pill{font-size:.74rem;font-weight:700;border-radius:999px;padding:2px 8px;white-space:nowrap}
.pill.ok{background:var(--leaf-soft);color:var(--leaf-deep)} .pill.no{background:var(--stone);color:var(--stone-text)}
.src{color:var(--muted);font-size:.8rem;margin-top:12px}

/* 코스 따라가기 */
.timeline{list-style:none;margin:0;padding:0 0 0 6px;display:grid;gap:0}
.timeline li{position:relative;padding:0 0 16px 26px}
.timeline li::before{content:"";position:absolute;left:5px;top:6px;bottom:-6px;border-left:3px solid var(--leaf-soft)}
.timeline li:last-child::before{display:none}
.timeline li::after{content:"";position:absolute;left:0;top:4px;width:13px;height:13px;border-radius:50%;background:var(--card);border:3px solid var(--leaf)}
.timeline li.caution::after{border-color:var(--red);background:#F8E1DE}
.timeline .m{font-weight:700;color:var(--leaf-deep);font-size:.88rem}
.timeline li.caution .m{color:var(--red)}
.timeline .t{font-size:.97rem}
.timeline .f{display:flex;flex-wrap:wrap;gap:4px;margin-top:4px}
.timeline .f span{font-size:.76rem;background:var(--paper);border:1px solid var(--stone-2);border-radius:999px;padding:1px 8px}

/* 가게·병원 카드 */
[class*="st-key-card_"]{background:var(--paper);border:1px solid var(--stone-2);border-radius:16px;padding:12px 14px}
.shop b{font-size:1.02rem;font-weight:700} .shop .meta{color:var(--muted);font-size:.88rem}
.shop .tags{display:flex;flex-wrap:wrap;gap:5px;margin-top:6px}
.tag{font-size:.76rem;font-weight:600;border-radius:999px;padding:2px 9px;background:var(--gyul-soft);color:var(--gyul-text)}
.tag.wc{background:var(--leaf-soft);color:var(--leaf-deep)} .tag.gray{background:var(--stone);color:var(--stone-text)} .tag.red{background:#F8E1DE;color:var(--red)}

/* 좁은 화면(휴대폰): 위 상단 바, 아래 시트형 대시보드, 대화창은 화면 전체 */
@media (max-width:639.98px){
  .st-key-topbar{top:8px;left:8px;right:8px;max-width:none;min-height:50px;padding:6px 8px 6px 10px;gap:6px!important;border-radius:16px}
  .st-key-topbar > [data-testid="stElementContainer"]:first-child{flex:1 1 0!important;min-width:0}
  .st-key-topbar .chips,.brand small{display:none}
  .brand b{font-size:1.05rem}
  .st-key-topbar [data-testid="stBaseButton-tertiary"] p{display:none}
  .st-key-topbar [data-testid="stBaseButton-tertiary"]{padding:4px 8px}
  .st-key-dash{top:auto;left:0;right:0!important;bottom:0;width:auto!important;height:46dvh;border-radius:22px 22px 0 0;padding:14px 14px 20px;border-bottom:none}
  .st-key-chatfab{right:14px;bottom:calc(46dvh + 14px)}
  .st-key-chatfab button{width:64px;height:64px;min-height:64px}
  .fab-hint{right:90px;bottom:calc(46dvh + 26px);font-size:.86rem}
  .searching{top:66px;left:8px}
  .st-key-chatwin{top:0;left:0;right:0;bottom:0;width:auto!important;border-radius:0}
  body:has(.st-key-chatwin) .st-key-chatfab,body:has(.st-key-chatwin) .fab-hint{display:none}
  .hero-art{display:none}
  .place-name{font-size:1.4rem}
}
</style>"""

BIG_CSS = "<style>html{font-size:125%}</style>"

ICON = {
    "check": '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>',
    "people": '<svg viewBox="0 0 24 24" fill="#fff"><circle cx="8" cy="7.5" r="3.2"/><circle cx="16.5" cy="8.5" r="2.6"/><path d="M2.5 19c0-3.4 2.5-6 5.5-6s5.5 2.6 5.5 6z"/><path d="M13.6 19c.2-2.2-.4-3.9-1.5-5.2.9-.6 2.1-1 3.4-1 3 0 5 2.4 5 5.6V19z"/></svg>',
    "question": '<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round"><path d="M9 9.2a3 3 0 1 1 4.3 2.7c-.9.5-1.3 1.1-1.3 2.1"/><circle cx="12" cy="17.6" r=".6" fill="#fff"/></svg>',
    "wheel": '<svg viewBox="0 0 24 24" fill="none" stroke="#1E5636" stroke-width="2" stroke-linecap="round"><circle cx="10" cy="4" r="1.6" fill="#1E5636"/><path d="M10 7v6h6l2.5 5"/><path d="M10 10h5"/><path d="M7.5 11.5a5 5 0 1 0 7 5.8"/></svg>',
    "stroller": '<svg viewBox="0 0 24 24" fill="none" stroke="#9C4A07" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5h2l1.5 7h10a6 6 0 0 0-6-6V5"/><path d="M7.5 12c.5 2.5 2.5 3.5 5 3.5h3"/><circle cx="9" cy="19" r="1.8"/><circle cx="16.5" cy="19" r="1.8"/></svg>',
    "pregnant": '<svg viewBox="0 0 24 24" fill="none" stroke="#9A3D6B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="4" r="1.8" fill="#9A3D6B"/><path d="M10 7.5c-1.5 1-2 3-1.5 5.5l1 8"/><path d="M11 8.5c3.5 1 5 3.5 4 6.5-.6 1.6-2.5 2-4.5 1.5"/><path d="M12.5 17l.5 4"/></svg>',
    "senior": '<svg viewBox="0 0 24 24" fill="none" stroke="#2C6EA6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="4" r="1.8" fill="#2C6EA6"/><path d="M11 7l-1.5 6 3 3 1 5"/><path d="M9.5 13l-2.5 8"/><path d="M11 8.5l3 2.5"/><path d="M17 11v10"/><path d="M15.5 11.2c.4-.6 1-1 1.5-1"/></svg>',
}

PORES = ('<defs><pattern id="pores" width="9" height="9" patternUnits="userSpaceOnUse">'
         '<rect width="9" height="9" fill="#585D62"/><circle cx="2" cy="3" r="1.15" fill="#3A3E42"/>'
         '<circle cx="6.6" cy="6.4" r=".85" fill="#41454A"/><circle cx="5.2" cy="1.4" r=".5" fill="#6E7378"/>'
         '<circle cx="1.2" cy="7.6" r=".6" fill="#44484D"/></pattern></defs>')


def img(svg, cls="", alt="", style=""):
    """svg 문자열을 <img>로. svg 안의 <style>(눈 깜빡임 등)은 그대로 동작한다."""
    if 'xmlns="http://www.w3.org/2000/svg"' not in svg.split(">", 1)[0]:
        svg = svg.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ', 1)
    data = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    a = f' alt="{escape(alt)}"' if alt else ' alt="" aria-hidden="true"'
    return f'<img class="{cls}" src="data:image/svg+xml;base64,{data}"{a} style="{style}">'


BLINK = ('<style>.pupil{transform-box:fill-box;transform-origin:center;animation:b 3.6s infinite}'
         '@keyframes b{0%,92%,100%{transform:scaleY(1)}95%{transform:scaleY(.1)}}'
         '@media (prefers-reduced-motion:reduce){.pupil{animation:none}}</style>')


def hareubang(cls="har"):
    """돌하르방: 벙거지 모자, 툭 튀어나온 눈, 긴 코, 배 위에 얹은 두 손. 직접 그린 단순한 모양."""
    return (f'<svg class="{cls}" viewBox="0 0 120 200" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="돌하르방">'
            f'{BLINK}{PORES}'
            '<path d="M29 50 Q28 9 60 8 Q92 9 91 50 Z" fill="url(#pores)" stroke="#2B2E31" stroke-width="2"/>'
            '<rect x="22" y="45" width="76" height="11" rx="5.5" fill="url(#pores)" stroke="#2B2E31" stroke-width="2"/>'
            '<path d="M28 55 Q22 122 30 196 L90 196 Q98 122 92 55 Z" fill="url(#pores)" stroke="#2B2E31" stroke-width="2"/>'
            '<circle cx="44" cy="76" r="11" fill="#6A6F74" stroke="#2B2E31" stroke-width="2.2"/>'
            '<circle cx="76" cy="76" r="11" fill="#6A6F74" stroke="#2B2E31" stroke-width="2.2"/>'
            '<circle class="pupil" cx="44" cy="77" r="4.4" fill="#25282B"/>'
            '<circle class="pupil" cx="76" cy="77" r="4.4" fill="#25282B"/>'
            '<path d="M60 74 Q51 100 53 113 Q60 120 67 113 Q69 100 60 74 Z" fill="#62676C" stroke="#2B2E31" stroke-width="1.8"/>'
            '<path d="M47 128 Q60 135 73 128" stroke="#2B2E31" stroke-width="3" fill="none" stroke-linecap="round"/>'
            '<rect x="33" y="146" width="36" height="12" rx="6" fill="#63686D" stroke="#2B2E31" stroke-width="1.8"/>'
            '<rect x="51" y="165" width="36" height="12" rx="6" fill="#63686D" stroke="#2B2E31" stroke-width="1.8"/>'
            '</svg>')


def gyul(cls="gyul"):
    return (f'<svg class="{cls}" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
            '<circle cx="20" cy="22" r="15" fill="#F0892B"/><circle cx="15" cy="17" r="4" fill="#F8B06A" opacity=".7"/>'
            '<circle cx="12" cy="25" r=".8" fill="#D9741A"/><circle cx="24" cy="29" r=".8" fill="#D9741A"/>'
            '<circle cx="27" cy="19" r=".8" fill="#D9741A"/>'
            '<path d="M20 8 Q27 2 33 6 Q27 12 20 8Z" fill="#2F7A4D"/><path d="M20 7.5v4" stroke="#1E5636" stroke-width="1.6"/></svg>')


def hero_scene():
    """시작 화면 그림: 귤빛 해, 한라산, 바다, 돌하르방, 귤."""
    har = hareubang("har").replace('<svg class="har" viewBox', '<svg class="har" x="128" y="58" width="108" height="180" viewBox')
    g1 = gyul().replace('<svg class="gyul" viewBox', '<svg x="238" y="206" width="34" height="34" viewBox')
    g2 = gyul().replace('<svg class="gyul" viewBox', '<svg x="268" y="214" width="26" height="26" viewBox')
    scene = ('<svg viewBox="0 0 360 250" xmlns="http://www.w3.org/2000/svg">'
            '<circle cx="262" cy="70" r="46" fill="#F0892B" opacity=".92"/>'
            '<path d="M0 170 Q70 120 130 128 Q180 70 225 96 Q290 128 360 150 L360 250 L0 250Z" fill="#7FB08A"/>'
            '<path d="M0 186 Q90 150 170 160 Q260 168 360 170 L360 250 L0 250Z" fill="#2F7A4D"/>'
            '<path d="M0 214 Q90 204 180 212 Q270 220 360 210 L360 250 L0 250Z" fill="#5E9BCF"/>'
            '<path d="M0 232 Q90 224 180 230 Q270 238 360 230 L360 250 L0 250Z" fill="#2C6EA6"/>'
            f'{har}{g1}{g2}</svg>')
    return f'<div class="hero-art">{img(scene, "scene", "한라산과 바다를 배경으로 선 돌하르방과 귤")}</div>'


def brand():
    mini = img(hareubang("har"), "mini", style="width:26px;height:42px")
    return (f'<div class="brand">{mini}<div><b>제주 같이나들이</b>'
            '<small>휠체어·유모차·어르신과 함께 가는 제주</small></div></div>')


def chips(items, gyul_first=False):
    out = "".join(f'<span class="chip{" gyul" if gyul_first and i == 0 else ""}">{escape(t)}</span>' for i, t in enumerate(items))
    return f'<div class="chips">{out}</div>'


def har_face():
    """챗봇 얼굴: 시작 화면 돌하르방과 같은 캐릭터(벙거지 모자, 툭 튀어나온 눈, 긴 코, 미소, 현무암 구멍).
    동그란 버튼을 꽉 채우도록 얼굴 폭만 넓혔다."""
    return ('<svg viewBox="0 5 100 100" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="돌하르방 도우미">'
            f'{BLINK}{PORES}'
            '<path d="M21 46 Q15 76 18 104 L82 104 Q85 76 79 46 Z" fill="url(#pores)" stroke="#2B2E31" stroke-width="2.2"/>'
            '<path d="M25 41 Q24 8 50 7 Q76 8 75 41 Z" fill="url(#pores)" stroke="#2B2E31" stroke-width="2.2"/>'
            '<rect x="15" y="37" width="70" height="10" rx="5" fill="url(#pores)" stroke="#2B2E31" stroke-width="2.2"/>'
            '<circle cx="36" cy="60" r="9.5" fill="#6A6F74" stroke="#2B2E31" stroke-width="2.2"/>'
            '<circle cx="64" cy="60" r="9.5" fill="#6A6F74" stroke="#2B2E31" stroke-width="2.2"/>'
            '<circle class="pupil" cx="36" cy="61" r="4" fill="#25282B"/>'
            '<circle class="pupil" cx="64" cy="61" r="4" fill="#25282B"/>'
            '<path d="M50 57 Q42.5 77 44.5 86 Q50 91 55.5 86 Q57.5 77 50 57 Z" fill="#62676C" stroke="#2B2E31" stroke-width="1.9"/>'
            '<path d="M39 95 Q50 101 61 95" stroke="#2B2E31" stroke-width="2.8" fill="none" stroke-linecap="round"/>'
            '</svg>')


def data_uri(svg):
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")


FAB_CSS = f'<style>:root{{--fab-img:url("{data_uri(har_face())}")}}</style>'


def avatar():
    return f'<div class="avatar">{img(har_face())}</div>'


def chat_head():
    return (f'<div class="chat-head">{avatar()}<div><b>하르방 도우미</b>'
            '<small>가고 싶은 곳, 함께 가는 분을 말해 주세요</small></div></div>')


def msg_user(text):
    return f'<div class="msg-me">{escape(text)}</div>'


def typing(steps):
    s = "".join(f"<span>{escape(t)}</span>" for t in steps[:3])
    return (f'<div class="typing" role="status" aria-live="polite">{avatar()}<div class="bub">'
            f'<span class="dots" aria-hidden="true"><i></i><i></i><i></i></span><div class="steps">{s}</div></div></div>')


def searching():
    return (f'<div class="searching" role="status">{img(gyul("g"))}하르방이 길을 살펴보고 있어요</div>')


def fab_hint():
    return '<div class="fab-hint" aria-hidden="true">하르방에게 물어보세요!</div>'


def dash_head(tag, note=""):
    return f'<div class="dash-head"><b>{escape(tag)}</b><span>{escape(note)}</span></div>'


def tip_line(text):
    return f'<div class="tip-line">{escape(text)}</div>'


def trace(steps):
    if not steps:
        return ""
    return '<div class="trace">' + "".join(f"<span>✓ {escape(s)}</span>" for s in steps) + "</div>"


def verdict(color, label, reason):
    cls, icon = VERDICT.get(color, ("stone", "question"))
    return (f'<div class="verdict {cls}"><div class="vi">{img(ICON[icon])}</div><div><div class="vl">{escape(label)}</div>'
            f'<div class="vr">{escape(reason)}</div></div></div>')


def place_head(name, where):
    return f'<div class="place-name">{escape(name)}</div><div class="place-where">{escape(where)}</div>'


def tiles(items):
    """items: [(제목, 값, 'yes'|'no'|'')]"""
    return '<div class="tiles">' + "".join(
        f'<div class="tile {state}"><small>{escape(k)}</small><b>{escape(v)}</b></div>' for k, v, state in items) + "</div>"


def notes(good, warn):
    li = [f'<li class="good"><i>✓</i><span>{escape(g)}</span></li>' for g in good]
    li += [f'<li class="warn"><i>!</i><span>{escape(w)}</span></li>' for w in warn]
    return f'<ul class="notes">{"".join(li)}</ul>' if li else ""


def weather(line, tips):
    tip = "<br>".join(escape(t) for t in tips)
    return (f'<div class="weather"><span>☂</span><div>{"<b>" + tip + "</b><br>" if tip else ""}'
            f'<span>{escape(line)}</span></div></div>')


def sect(title):
    return f'<div class="sect">{escape(title)}</div>'


def checks(rows):
    out = "".join(f'<div><b>{escape(c["item"])}</b><span>{escape(c["status"])}</span>'
                  f'<span class="pill {"ok" if c["known"] else "no"}">{"확인됨" if c["known"] else "확인 안 됨"}</span></div>'
                  for c in rows)
    return f'<div class="checks">{out}</div>'


def timeline(points, not_caution):
    li = []
    for p in points:
        caution = any(f not in not_caution for f in p["flags"])
        tags = "".join(f"<span>{escape(f)}</span>" for f in p["flags"])
        li.append(f'<li class="{"caution" if caution else ""}"><div class="m">출발 후 약 {p["at_m"]}m</div>'
                  f'<div class="t">{escape(p["label"])}</div><div class="f">{tags}</div></li>')
    return f'<ul class="timeline">{"".join(li)}</ul>'


def shop(name, meta, tags):
    """tags: [(글자, 'wc'|'gray'|'red'|'')]"""
    t = "".join(f'<span class="tag {c}">{escape(x)}</span>' for x, c in tags)
    return f'<div class="shop"><b>{escape(name)}</b><div class="meta">{escape(meta)}</div><div class="tags">{t}</div></div>'


def src(text):
    return f'<div class="src">{escape(text)}</div>'


def choice(icon, title, desc, bg):
    return (f'<div class="choice"><div class="ic" style="background:{bg}">{img(ICON[icon])}</div>'
            f'<div><b>{escape(title)}</b><span>{escape(desc)}</span></div></div>')


def hello():
    return ('<div class="hello"><span class="eyebrow">공공데이터로 미리 확인해요</span>'
            '<h1>우리 가족이 갈 수 있을까?</h1>'
            '<p>경사·계단·턱, 장애인 화장실과 쉴 곳까지 먼저 살펴보고 알려드려요.</p></div>')
