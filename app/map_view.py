"""화면 전체에 깔리는 지도. 카카오맵 JavaScript SDK로 그리고, 키가 없으면 Streamlit 기본 지도로 보여준다.

키: .env 의 KAKAO_JS_KEY (카카오 개발자 > 내 애플리케이션 > 앱 키 > JavaScript 키).
     플랫폼 > Web 에 http://localhost:8501 등록, 카카오맵 사용 설정 ON 필요.

st.components.v2 컴포넌트라서 지도는 한 번만 만들고, 다시 그릴 때는 표식만 바꾼다(깜빡임 없음).
지도는 제주도 안에서만 움직이고(축소 한도 + 중심 고정), 추천 장소를 누르면 Python 쪽으로 'pick',
나들이 장소 점의 '이곳 살펴보기'를 누르면 'look' 신호를 보낸다.
"""
import json
import os

import pandas as pd
import streamlit as st

from ui import VERDICT_HEX  # noqa: E402  판정 색은 화면과 같은 값

CAUTION_HEX = "#B83227"
ROUTE_HEX = "#2F7A4D"
FOOD_HEX = "#E07A1C"   # 귤색
HELP_HEX = "#5B3A8C"
HELP_SHORT = {"약국": "약", "병·의원": "병", "응급실": "응"}
NOT_CAUTION = {"장애인 화장실", "장애인 주차"}


def kakao_key():
    return os.getenv("KAKAO_JS_KEY", "").strip()


def build(results=None, selected=None, detail=None, food=None, help_=None, all_places=None):
    """지도에 올릴 표식 목록을 만든다. 화면 상태(추천·식당·병원)에 따라 필요한 것만 담는다."""
    marks, route = [], []
    if results:
        for i, r in enumerate(results, 1):
            marks.append({"kind": "place", "lat": r["lat"], "lon": r["lon"], "text": str(i),
                          "name": r["place"], "sub": r["verdict"], "color": VERDICT_HEX.get(r["verdict_color"], "#5F6B73"),
                          "big": r["place"] == selected, "fit": r["place"] == selected or not selected})
    elif all_places is not None:
        for _, r in all_places.iterrows():
            marks.append({"kind": "dot", "lat": float(r["start_lat"]), "lon": float(r["start_lon"]),
                          "name": r["place"], "sub": f"{r['sigungu']} {r['dong']}", "color": ROUTE_HEX})
    if detail and detail.get("all_points"):
        for p in detail["all_points"]:
            route.append([p["lat"], p["lon"]])
            caution = [f for f in p["flags"] if f not in NOT_CAUTION]
            if caution:
                marks.append({"kind": "caution", "lat": p["lat"], "lon": p["lon"], "text": "!",
                              "name": f"출발 후 약 {p['at_m']}m", "sub": " · ".join(caution), "color": CAUTION_HEX})
            elif "장애인 화장실" in p["flags"]:
                marks.append({"kind": "toilet", "lat": p["lat"], "lon": p["lon"], "text": "WC",
                              "name": "장애인 화장실", "sub": p["label"], "color": ROUTE_HEX})
    if food:
        for i, it in enumerate(food.get("items", []), 1):
            marks.append({"kind": "food", "lat": it["lat"], "lon": it["lon"], "text": "식",
                          "name": it["name"], "sub": it["food_type"] + (" · 휠체어 진입 확인" if it["wheelchair_entry"] else ""),
                          "color": FOOD_HEX, "ring": it["wheelchair_entry"]})
    if help_:
        for kind, items in help_.get("help", {}).items():
            for it in items:
                if it.get("lat") is None:
                    continue
                marks.append({"kind": "help", "lat": it["lat"], "lon": it["lon"], "text": HELP_SHORT.get(kind, "+"),
                              "name": it["name"], "sub": f"{kind} · {it['km']}km", "color": HELP_HEX})
    return {"marks": marks, "route": route}


LEGEND = [("place", "추천 장소(번호)", VERDICT_HEX["green"]), ("route", "코스", ROUTE_HEX),
          ("dot", "나들이 장소 70곳", ROUTE_HEX), ("caution", "확인할 지점", CAUTION_HEX),
          ("toilet", "장애인 화장실", ROUTE_HEX), ("food", "식당", FOOD_HEX), ("help", "약국·병원", HELP_HEX)]


def legend_items(data):
    kinds = {m["kind"] for m in data["marks"]} | ({"route"} if data["route"] else set())
    return [(label, color) for k, label, color in LEGEND if k in kinds]


def legend(data):
    return [label for label, _ in legend_items(data)]


# ---------- 카카오맵 컴포넌트 ----------
_CSS = """
.km-root{position:fixed;inset:0;z-index:0;background:#DCE8EE;font-family:"Pretendard Variable",Pretendard,"Malgun Gothic",sans-serif}
.km-map{position:absolute;inset:0}
.km-mk{display:flex;align-items:center;justify-content:center;border-radius:999px;color:#fff;font-weight:700;
  border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.35);cursor:pointer;font-size:13px;width:28px;height:28px;font-family:inherit}
.km-mk.big{width:42px;height:42px;font-size:18px;border-width:3px;box-shadow:0 0 0 5px rgba(240,137,43,.35),0 2px 6px rgba(0,0,0,.35)}
.km-mk.dot{width:13px;height:13px;border-width:2px}
.km-mk.dot:hover{transform:scale(1.4)}
.km-mk.caution,.km-mk.toilet{width:22px;height:22px;font-size:11px}
.km-mk.help{border-radius:6px}
.km-mk.ring{box-shadow:0 0 0 3px #2F7A4D,0 1px 4px rgba(0,0,0,.35)}
.km-mk:focus-visible{outline:3px solid #16202A;outline-offset:2px}
.km-tip{background:#fff;color:#16202A;border:1px solid #D7D9D3;border-radius:12px;padding:9px 11px;font-size:14px;
  line-height:1.4;box-shadow:0 4px 14px rgba(0,0,0,.2);margin-bottom:44px;max-width:230px;white-space:normal;font-family:inherit}
.km-tip b{display:block;font-weight:700} .km-tip small{color:#4F5D66}
.km-tip a,.km-tip button{display:inline-block;margin-top:7px;color:#1E5636;font-weight:700;text-decoration:none;font:inherit;font-weight:700;
  background:#E3F1E7;border:none;border-radius:999px;padding:4px 10px;cursor:pointer}
.km-legend{position:absolute;left:64px;bottom:16px;z-index:3;background:rgba(255,255,255,.95);border-radius:12px;
  padding:7px 11px;font-size:13px;color:#16202A;display:flex;flex-wrap:wrap;gap:4px 12px;max-width:min(560px,calc(100% - 140px));
  box-shadow:0 2px 8px rgba(0,0,0,.12)}
.km-legend span{display:inline-flex;align-items:center;gap:5px}
.km-legend i{display:inline-block;width:10px;height:10px;border-radius:50%}
.km-err{display:none;position:absolute;inset:0;align-items:center;justify-content:center;text-align:center;padding:20px;
  background:#E8E9E5;color:#1D2124;font-size:15px}
@media (max-width:639.98px){.km-legend{top:66px;bottom:auto;left:8px;font-size:12px;max-width:calc(100% - 16px)}}
"""

_JS = r"""
const JEJU = {s: 33.05, n: 33.66, w: 126.05, e: 127.08};   // 지도 중심이 이 밖으로 못 나간다
const ORDER = {dot: 1, toilet: 2, caution: 3, help: 4, food: 5, place: 6};

function esc(t) {
  return String(t ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'})[c]);
}

function sdk(key) {
  if (window.kakao && window.kakao.maps && window.kakao.maps.Map) return Promise.resolve();
  if (!window.__jejuKakao) {
    window.__jejuKakao = new Promise((ok, bad) => {
      const s = document.createElement('script');
      s.src = 'https://dapi.kakao.com/v2/maps/sdk.js?autoload=false&appkey=' + encodeURIComponent(key);
      s.onerror = bad;
      s.onload = () => (window.kakao && window.kakao.maps) ? window.kakao.maps.load(ok) : bad();
      document.head.appendChild(s);
    }).catch(e => { window.__jejuKakao = null; throw e; });
  }
  return window.__jejuKakao;
}

function small() { return window.innerWidth < 640; }

// 지도 위에 떠 있는 상단 바·대시보드·대화창에 가리지 않게 여백을 둔다 [위, 오른쪽, 아래, 왼쪽]
function pads(D) {
  const w = window.innerWidth, h = window.innerHeight;
  if (small()) return [76, 28, D.panel ? Math.round(h * 0.46) + 28 : 40, 28];
  let r = 40;
  if (D.chat) r += 396;
  if (D.panel && !(D.chat && w <= 1180)) r += 436;
  return [96, Math.min(r, w - 280), 40, 56];
}

function closeTip(S) { if (S.open) { S.open.setMap(null); S.open = null; } }

function fit(S) {
  const map = S.map;
  map.relayout();
  const [t, r, b, l] = pads(S.data);
  map.setBounds(S.bounds || S.jeju, t, r, b, l);
}

function init(root, S) {
  const k = window.kakao.maps;
  const box = root.querySelector('.km-map');
  const map = new k.Map(box, {center: new k.LatLng(33.38, 126.55), level: small() ? 11 : 10});
  map.setMaxLevel(small() ? 11 : 10);   // 더 멀리 줄여서 육지까지 보이지 않게
  if (!small()) map.addControl(new k.ZoomControl(), k.ControlPosition.BOTTOMLEFT);
  S.map = map; S.layers = []; S.open = null;
  S.jeju = new k.LatLngBounds(new k.LatLng(33.19, 126.15), new k.LatLng(33.57, 126.97));
  const clamp = () => {
    const c = map.getCenter();
    const lat = Math.min(JEJU.n, Math.max(JEJU.s, c.getLat()));
    const lng = Math.min(JEJU.e, Math.max(JEJU.w, c.getLng()));
    if (lat !== c.getLat() || lng !== c.getLng()) map.panTo(new k.LatLng(lat, lng));
  };
  k.event.addListener(map, 'dragend', clamp);
  k.event.addListener(map, 'zoom_changed', clamp);
  k.event.addListener(map, 'click', () => closeTip(S));
  let t;
  window.addEventListener('resize', () => { clearTimeout(t); t = setTimeout(() => fit(S), 200); });
}

function draw(root, S) {
  const k = window.kakao.maps, D = S.data, map = S.map;
  const leg = root.querySelector('.km-legend');
  leg.innerHTML = (D.legend || []).map(([t, c]) => `<span><i style="background:${esc(c)}"></i>${esc(t)}</span>`).join('');
  leg.style.display = (D.legend || []).length ? '' : 'none';

  const sig = JSON.stringify([D.marks, D.route]);
  const psig = JSON.stringify(pads(D));
  if (sig === S.sig) {                      // 표식이 같으면 사용자가 옮긴 화면을 그대로 둔다
    if (psig !== S.psig) { S.psig = psig; fit(S); }
    return;
  }
  S.sig = sig; S.psig = psig;
  closeTip(S);
  S.layers.forEach(o => o.setMap(null));
  S.layers = [];

  const b = new k.LatLngBounds();
  let n = 0;
  if (D.route.length > 1) {
    const path = D.route.map(p => new k.LatLng(p[0], p[1]));
    S.layers.push(new k.Polyline({map, path, strokeWeight: 6, strokeColor: '#2F7A4D', strokeOpacity: 0.85}));
    path.forEach(p => { b.extend(p); n++; });
  }
  D.marks.forEach(m => {
    const pos = new k.LatLng(m.lat, m.lon);
    if (m.fit !== false && m.kind !== 'dot') { b.extend(pos); n++; }
    const el = document.createElement('div');
    el.className = 'km-mk ' + m.kind + (m.big ? ' big' : '') + (m.ring ? ' ring' : '');
    el.style.background = m.color;
    el.textContent = m.text || '';
    el.tabIndex = 0;
    el.setAttribute('role', 'button');
    el.setAttribute('aria-label', m.name + ', ' + (m.sub || ''));
    S.layers.push(new k.CustomOverlay({map, position: pos, content: el, yAnchor: 0.5, zIndex: ORDER[m.kind] + (m.big ? 10 : 0)}));

    const tip = document.createElement('div');
    tip.className = 'km-tip';
    let act = '';
    if (m.kind === 'place' || m.kind === 'food' || m.kind === 'help')
      act = `<a href="https://map.kakao.com/link/to/${encodeURIComponent(m.name)},${m.lat},${m.lon}" target="_blank" rel="noopener">길안내 열기</a>`;
    if (m.kind === 'dot') act = '<button type="button" data-look="1">이곳 살펴보기</button>';
    tip.innerHTML = `<b>${esc(m.name)}</b><small>${esc(m.sub)}</small>${act ? '<br>' + act : ''}`;
    const btn = tip.querySelector('[data-look]');
    if (btn) btn.addEventListener('click', e => { e.stopPropagation(); closeTip(S); S.trigger('look', m.name); });
    const info = new k.CustomOverlay({position: pos, content: tip, yAnchor: 1, zIndex: 50});
    const act2 = () => {
      if (m.kind === 'place' && !m.big) { S.trigger('pick', m.name); return; }   // 다른 후보를 누르면 그 장소로
      const same = S.open === info;
      closeTip(S);
      if (!same) { info.setMap(map); S.open = info; }
    };
    el.addEventListener('click', e => { e.stopPropagation(); act2(); });
    el.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); act2(); } });
  });

  if (n) {   // 한 점만 있으면 너무 확대되지 않게 둘레를 조금 넓힌다
    const sw = b.getSouthWest(), ne = b.getNorthEast(), d = 0.004;
    if (ne.getLat() - sw.getLat() < 2 * d) { b.extend(new k.LatLng(sw.getLat() - d, sw.getLng())); b.extend(new k.LatLng(ne.getLat() + d, ne.getLng())); }
    if (ne.getLng() - sw.getLng() < 2 * d) { b.extend(new k.LatLng(sw.getLat(), sw.getLng() - d)); b.extend(new k.LatLng(ne.getLat(), ne.getLng() + d)); }
  }
  S.bounds = n ? b : null;
  fit(S);
}

export default function (component) {
  const { data, parentElement, setTriggerValue } = component;
  const D = typeof data === 'string' ? JSON.parse(data) : (data || {});
  let root = parentElement.querySelector('.km-root');
  if (!root) {
    root = document.createElement('div');
    root.className = 'km-root';
    root.innerHTML = '<div class="km-map" role="application" aria-label="제주 나들이 지도"></div><div class="km-legend"></div>'
      + '<div class="km-err">카카오맵을 불러오지 못했어요.<br>KAKAO_JS_KEY와 등록한 사이트 주소를 확인해 주세요.</div>';
    parentElement.appendChild(root);
  }
  const S = root.__s || (root.__s = {});
  S.data = D;
  S.trigger = setTriggerValue;
  sdk(D.key).then(() => {
    if (!S.map) init(root, S);
    draw(root, S);
  }).catch(() => { root.querySelector('.km-err').style.display = 'flex'; });
}
"""

_KMAP = st.components.v2.component("jeju_kmap", css=_CSS, js=_JS, isolate_styles=False)


def _noop():
    pass


def render(data, panel=True, chat=False, key="kmap"):
    """지도를 그린다. 카카오맵이면 {'pick': 장소명|None, 'look': 장소명|None} 을 돌려준다."""
    if not kakao_key():
        _fallback(data)
        return {}
    payload = {"key": kakao_key(), "marks": data["marks"], "route": data["route"],
               "legend": legend_items(data), "panel": panel, "chat": chat}
    res = _KMAP(key=key, data=json.dumps(payload, ensure_ascii=False), height=1,
                on_pick_change=_noop, on_look_change=_noop)
    return {"pick": getattr(res, "pick", None), "look": getattr(res, "look", None)}


def _fallback(data):
    rows = [{"lat": m["lat"], "lon": m["lon"], "color": m["color"],
             "size": 40 if m["kind"] in ("place", "food", "help") else 18} for m in data["marks"]]
    rows += [{"lat": a, "lon": b, "color": ROUTE_HEX + "88", "size": 6} for a, b in data["route"]]
    df = pd.DataFrame(rows) if rows else pd.DataFrame([{"lat": 33.38, "lon": 126.55, "color": ROUTE_HEX, "size": 1}])
    with st.container(key="mapbox"):
        st.map(df, latitude="lat", longitude="lon", color="color", size="size", height=800,
               alt="지도. " + ", ".join(legend(data)))
