"""데모 영상 자동 녹화: 실제 화면을 정해진 대본대로 조작하며 녹화한다.

- 보이는 마우스 커서가 누를 곳까지 부드럽게 움직이고, 누르면 물결이 퍼진다
- 중요한 순간에는 커서 쪽으로 화면이 부드럽게 확대됐다가 빠진다(따라가는 확대)
- 장면마다 아래 자막(단계 번호 + 한 줄 설명), 처음·끝에 제목 화면
- PC(1600×900)와 휴대폰(390×844) 장면을 녹화해 하나의 mp4로 잇는다

실행: python scripts/10_demo_record.py [--url http://localhost:3000] [--out final/6_데모_영상]
필요: pip install playwright imageio-ffmpeg && python -m playwright install chromium
"""
import argparse
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
W, H = 1600, 900

# ---------- 화면에 넣는 연출(커서·물결·확대·자막·제목) ----------
OVERLAY_JS = r"""
(() => {
  if (window.__demo) return;
  const st = document.createElement('style');
  st.textContent = `
  #demo-cursor{position:fixed;left:0;top:0;width:30px;height:30px;z-index:2147483647;pointer-events:none;
    transform:translate(-100px,-100px);transition:transform .7s cubic-bezier(.22,.8,.25,1);filter:drop-shadow(0 2px 3px rgba(0,0,0,.35))}
  .demo-ripple{position:fixed;z-index:2147483646;pointer-events:none;width:18px;height:18px;margin:-9px 0 0 -9px;border-radius:50%;
    border:3px solid #F0892B;animation:demoRip .6s ease-out forwards}
  @keyframes demoRip{from{opacity:1;transform:scale(.4)}to{opacity:0;transform:scale(3.2)}}
  #demo-cap{position:fixed;left:50%;bottom:34px;transform:translate(-50%,20px);opacity:0;z-index:2147483645;pointer-events:none;
    background:rgba(22,32,42,.90);color:#fff;border-radius:16px;padding:14px 26px 14px 18px;display:flex;align-items:center;gap:14px;
    font-family:Pretendard,'Noto Sans KR',sans-serif;box-shadow:0 8px 24px rgba(0,0,0,.25);transition:all .45s ease;max-width:86vw}
  #demo-cap.on{opacity:1;transform:translate(-50%,0)}
  #demo-cap .n{flex:0 0 auto;width:40px;height:40px;border-radius:50%;background:#F0892B;color:#2A1606;font-weight:900;font-size:20px;
    display:grid;place-items:center}
  #demo-cap b{display:block;font-size:22px;font-weight:800;line-height:1.3}
  #demo-cap small{display:block;font-size:16px;color:#D6DCE0;margin-top:2px;line-height:1.4}
  #demo-card{position:fixed;inset:0;z-index:2147483647;display:flex;flex-direction:column;align-items:center;justify-content:center;
    background:linear-gradient(160deg,#FBF3E8 0%,#F7EBDD 55%,#E3EFE6 100%);font-family:Pretendard,'Noto Sans KR',sans-serif;
    opacity:0;transition:opacity .6s ease;pointer-events:none;text-align:center;color:#1E2529}
  #demo-card.on{opacity:1}
  #demo-card .k{font-size:22px;font-weight:800;color:#B4610F;letter-spacing:.02em}
  #demo-card h1{font-size:64px;margin:14px 0 10px;letter-spacing:-.02em}
  #demo-card p{font-size:26px;margin:0;color:#46515A;line-height:1.5}
  #demo-card .u{margin-top:28px;font-size:22px;font-weight:700;background:#fff;border:2px solid #F0892B;border-radius:999px;padding:8px 22px}
  .demo-zoom{transition:transform .9s cubic-bezier(.22,.8,.25,1)}
  `;
  document.head.appendChild(st);
  const c = document.createElement('div');
  c.id = 'demo-cursor';
  c.innerHTML = '<svg viewBox="0 0 24 24" width="30" height="30"><path d="M3 2l7.5 19 2.6-7.6L21 10.8z" fill="#fff" stroke="#16202A" stroke-width="1.6" stroke-linejoin="round"/></svg>';
  document.body.appendChild(c);
  const cap = document.createElement('div');
  cap.id = 'demo-cap';
  document.body.appendChild(cap);
  const card = document.createElement('div');
  card.id = 'demo-card';
  document.body.appendChild(card);
  const zt = () => document.querySelector('.app') || document.documentElement;
  zt().classList.add('demo-zoom');
  window.__demo = {
    x: -100, y: -100,
    move(x, y) { this.x = x; this.y = y; c.style.transform = `translate(${x - 4}px, ${y - 2}px)`; },
    ripple(x, y) { const r = document.createElement('div'); r.className = 'demo-ripple'; r.style.left = x + 'px'; r.style.top = y + 'px';
      document.body.appendChild(r); setTimeout(() => r.remove(), 700); },
    caption(n, t, s) { cap.innerHTML = (n ? `<span class="n">${n}</span>` : '') + `<div><b>${t}</b>${s ? `<small>${s}</small>` : ''}</div>`;
      cap.classList.add('on'); },
    hide() { cap.classList.remove('on'); },
    card(k, t, p, u) { card.innerHTML = `<div class="k">${k}</div><h1>${t}</h1><p>${p}</p>${u ? `<div class="u">${u}</div>` : ''}`;
      card.classList.add('on'); },
    uncard() { card.classList.remove('on'); },
    zoom(x, y, s) { const h = zt(); h.classList.add('demo-zoom'); h.style.transformOrigin = `${x}px ${y}px`; h.style.transform = `scale(${s})`; },
    unzoom() { zt().style.transform = 'none'; },
  };
})();
"""


class Demo:
    def __init__(self, page):
        self.page = page

    def setup(self):
        self.page.evaluate(OVERLAY_JS)

    def wait(self, s):
        self.page.wait_for_timeout(int(s * 1000))

    def center(self, loc):
        loc.scroll_into_view_if_needed(timeout=8000)
        b = loc.bounding_box()
        return b["x"] + b["width"] / 2, b["y"] + b["height"] / 2

    def move_to(self, loc, pause=0.75):
        x, y = self.center(loc)
        self.page.evaluate(f"window.__demo.move({x}, {y})")
        self.wait(pause)
        return x, y

    def click(self, loc, pause=0.75, after=0.6):
        self.unzoom()
        x, y = self.move_to(loc, pause)
        self.page.evaluate(f"window.__demo.ripple({x}, {y})")
        loc.click(timeout=10000)
        self.wait(after)
        return x, y

    def type(self, loc, text, delay=70):
        self.click(loc, after=0.3)
        loc.type(text, delay=delay)
        self.wait(0.4)

    def caption(self, n, t, s=""):
        self.page.evaluate("([n,t,s]) => window.__demo.caption(n,t,s)", [n, t, s])

    def hide(self):
        self.page.evaluate("window.__demo.hide()")

    def zoom_on(self, loc, s=1.45, hold=2.5):
        """그 부분이 든 패널·대화창만 커서 쪽으로 확대한다(지도까지 키우면 지도가 다시 그려지며 잠깐 비어 보인다)"""
        self.move_to(loc, 0.5)
        loc.evaluate("""(el, s) => {
          const c = el.closest('#chatwin, .dash') || document.querySelector('.app');
          const r = el.getBoundingClientRect(), cr = c.getBoundingClientRect();
          c.classList.add('demo-zoom');
          c.style.transformOrigin = `${r.left + r.width / 2 - cr.left}px ${r.top + Math.min(r.height, 260) / 2 - cr.top}px`;
          c.style.transform = `scale(${s})`;
          c.style.zIndex = 60;
          window.__demoZoomEl = c;
        }""", s)
        self.wait(hold)

    def unzoom(self):
        self.page.evaluate("""() => { const c = window.__demoZoomEl; if (c) { c.style.transform = 'none'; c.style.zIndex = ''; }
          window.__demoZoomEl = null; window.__demo.unzoom(); }""")
        self.wait(0.5)

    def card(self, k, t, p, u="", hold=3.5):
        self.page.evaluate("([k,t,p,u]) => window.__demo.card(k,t,p,u)", [k, t, p, u])
        self.wait(hold)

    def uncard(self):
        self.page.evaluate("window.__demo.uncard()")
        self.wait(0.8)

    def ask(self, text, timeout=60):
        """질문을 쳐서 보내고 답이 붙을 때까지 기다린다(보내기 전에 답 개수를 세어 둔다)"""
        self.type(self.page.locator("#chat-text"), text)
        n0 = self.page.locator(".bot").count()
        self.page.keyboard.press("Enter")
        self.wait_answer(timeout, n0)

    def wait_answer(self, timeout=60, n0=None):
        """하르방 답이 다 올 때까지(입력 중 표시가 사라지고 새 답이 붙을 때까지)"""
        n0 = self.page.locator(".bot").count() if n0 is None else n0
        t0 = time.time()
        while time.time() - t0 < timeout:
            if self.page.locator(".typing").count() == 0 and self.page.locator(".bot").count() > n0:
                break
            self.wait(0.3)
        self.wait(1.0)


def desktop(pw, url, outdir):
    browser = pw.chromium.launch()
    ctx = browser.new_context(viewport={"width": W, "height": H}, device_scale_factor=1,
                              record_video_dir=str(outdir), record_video_size={"width": W, "height": H}, locale="ko-KR")
    page = ctx.new_page()
    page.goto(url, wait_until="load")
    page.wait_for_timeout(2500)
    d = Demo(page)
    d.setup()

    # 0. 제목
    d.card("제주 AI·빅데이터 활용 AI Agent 개발 챌린지", "제주 같이나들이",
           "휠체어·유모차·어르신·임산부와 함께하는 제주 나들이<br>\"우리 가족이 갈 수 있을까, 뭘 조심할까\"에 답하는 AI Agent", "", 4.2)
    d.uncard()

    # 1. 누구와 · 어디로
    d.caption(1, "누구와, 어디로 가는지만 고르면 돼요", "숫자를 묻지 않아요. 고른 동네로 지도가 바로 이동해요")
    d.wait(1.2)
    d.click(page.get_by_role("radio", name="성산·구좌"), after=2.4)
    d.zoom_on(page.locator(".choices"), 1.25, 1.8)
    d.click(page.get_by_role("button", name="휠체어 타는 가족 갈 곳 찾기"), after=0.5)
    page.wait_for_selector(".tabs", timeout=60000)
    d.wait(2.2)

    # 2. 판정 + 근거
    d.caption(2, "갈 수 있는지 먼저 판정하고, 근거를 보여 줘요", "입구 턱·장애인 화장실·주차를 한 줄씩, 확인 안 된 것은 \"확인 안 됨\"")
    d.zoom_on(page.locator(".facts").first, 1.5, 2.8)
    ev = page.locator(".ev-toggle").first
    if ev.count():
        d.click(ev, after=1.2)
        d.caption(2, "판정 근거: 공공데이터 조사 원문 그대로", "제주데이터허브·한국관광공사 기록, 기준일과 출처 함께")
        d.zoom_on(page.locator(".evidence").first, 1.35, 3.2)
        d.click(ev, after=0.6)
    d.unzoom()

    # 3. 코스 (코스 조사가 있는 후보로)
    d.caption(3, "코스를 따라 조심할 곳을 미리 봐요", "지도에 경사·턱 지점, 넓은 화장실, 가까운 정류소")
    cands = page.locator(".cand")
    for i in range(min(cands.count(), 3)):
        d.click(cands.nth(i), after=1.2)
        d.click(page.locator("#tab-코스"), after=1.6)
        if page.locator(".timeline").count():
            break
        d.click(page.locator("#tab-한눈에"), after=0.6)
    if page.locator(".timeline").count():
        d.zoom_on(page.locator(".timeline").first, 1.35, 3.0)
    d.unzoom()

    # 4. 식당 → 지도와 연결
    d.click(page.locator("#tab-식당"), after=2.5)
    d.caption(4, "근처 식당은 1층·입구 턱 정보와 전화번호까지", "카드의 '지도'를 누르면 지도가 그 가게를 가리켜요")
    page.wait_for_selector(".tabpanel .cards .card", timeout=30000)
    mb = page.locator(".tabpanel .cards .card").nth(0).get_by_role("button", name="지도에서 보기")
    if mb.count() == 0:
        mb = page.locator(".tabpanel .cards .card").nth(0).locator("button", has_text="지도")
    if mb.count():
        d.click(mb.first, after=2.6)
    d.wait(1.0)

    # 5. 병원·약국
    d.click(page.locator("#tab-병원·약국"), after=2.5)
    d.caption(5, "가까운 약국·병원·응급실", "폐업한 약국은 빼고, 직선거리와 전화번호를 함께")
    d.wait(2.6)

    # 6. 큰 글씨
    d.caption(6, "글씨가 작으면 '큰 글씨' 한 번", "어르신도 읽기 쉽게 화면 전체가 커져요")
    big = page.get_by_role("switch", name="큰 글씨")
    d.click(big, after=2.4)
    d.click(big, after=1.0)

    # 7. 도우미: 평소 말투 (처음으로 돌아가 새로 시작: 앞에서 고른 '휠체어 가족'이 이어지지 않게)
    d.hide()
    home = page.get_by_role("button", name="처음으로")
    if home.count() and home.first.is_enabled():
        d.click(home.first, after=1.4)
    d.click(page.locator("#chatfab"), after=1.2)
    d.caption(7, "평소 말투로 물어보세요", "누가 함께 가는지, 어디 근처인지만 말해도 알아들어요")
    d.ask("할머니가 이가 안 좋으신데 공항 근처에서 먹을 곳 있을까?")
    d.caption(7, "1순위 한 곳을 정리해서, 확인할 점과 함께", "장애를 말하지 않았으면 '장애인' 대신 일상어로 답해요")
    d.zoom_on(page.locator(".bot").last.locator(".ans"), 1.35, 3.0)
    first_map = page.locator(".bot").last.locator(".mitems li").first.locator("button", has_text="지도")
    if first_map.count():
        d.click(first_map.first, after=3.0)

    # 8. 날씨까지
    d.caption(8, "날씨를 먼저 확인하고, 비 오면 갈 실내 장소도", "")
    d.ask("내일 휠체어 타는 아빠랑 바다 보러 가도 될까?")
    d.zoom_on(page.locator(".bot").last.locator(".ans"), 1.3, 2.8)
    d.unzoom()

    # 9. 임의로 정하지 않기
    d.caption(9, "기준을 임의로 정하지 않아요", "시 이름만 말하면 어디 근처인지, 또는 내 위치로 찾을지 되물어요")
    d.ask("서귀포 약국 알려줘")
    d.wait(1.6)

    # 10. 할 수 없는 일
    d.caption(10, "할 수 없는 일은 분명하게", "예약·맛 순위·의학적 판단은 하지 않고, 할 수 있는 일을 안내해요")
    d.ask("식당 예약 좀 해줘")
    d.wait(1.8)
    d.hide()
    d.unzoom()

    ctx.close()
    browser.close()


def phone(pw, url, outdir):
    browser = pw.chromium.launch()
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True,
                              record_video_dir=str(outdir), record_video_size={"width": 390, "height": 844}, locale="ko-KR")
    page = ctx.new_page()
    page.goto(url, wait_until="load")
    page.wait_for_timeout(2500)
    d = Demo(page)
    d.setup()
    d.caption("", "휴대폰도 같은 주소로", "")
    d.wait(1.5)
    d.click(page.get_by_role("radio", name="중문·서귀포"), after=1.4)
    d.click(page.get_by_role("button", name="아기와 유모차 갈 곳 찾기"), after=0.5)
    page.wait_for_selector(".tabs", timeout=60000)
    d.caption("", "유모차 대여·수유실까지", "")
    d.wait(3.2)
    d.click(page.locator(".sheet-handle"), after=2.4)
    d.hide()
    ctx.close()
    browser.close()


def end_card(pw, outdir):
    browser = pw.chromium.launch()
    ctx = browser.new_context(viewport={"width": W, "height": H}, record_video_dir=str(outdir), record_video_size={"width": W, "height": H})
    page = ctx.new_page()
    page.set_content("<html><body style='margin:0;background:#FBF3E8'></body></html>")
    d = Demo(page)
    d.setup()
    d.card("공공데이터 근거로, 함께 가는 가족에 맞춰", "제주 같이나들이",
           "제주데이터허브 무장애 조사 1,480개 지점 · 한국관광공사 무장애 정보 · 공중화장실 · 상가·음식점·약국·버스 정류소",
           "jeju-gachi.vercel.app", 4.5)
    ctx.close()
    browser.close()


def latest_video(d):
    vids = sorted(Path(d).glob("*.webm"), key=lambda p: p.stat().st_mtime)
    return vids[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:3000")
    ap.add_argument("--out", default=str(ROOT / "final" / "6_데모_영상"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="demo_"))
    parts = []
    with sync_playwright() as pw:
        for name, fn in (("pc", lambda d: desktop(pw, args.url, d)), ("phone", lambda d: phone(pw, args.url, d)),
                         ("end", lambda d: end_card(pw, d))):
            d = tmp / name
            d.mkdir()
            fn(d)
            parts.append(latest_video(d))
            print("녹화", name, parts[-1].stat().st_size // 1024, "KB", flush=True)
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    # 휴대폰 장면은 가운데에 세워 1600×900 배경 위에 놓는다
    mp4s = []
    for i, p in enumerate(parts):
        o = tmp / f"p{i}.mp4"
        if "phone" in str(p.parent):
            vf = (f"scale=-2:{H - 60},pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0xFBF3E8,fps=30")
        else:
            vf = f"scale={W}:{H},fps=30"
        skip = ["-ss", "2.6"] if "end" not in str(p.parent) else ["-ss", "0.3"]  # 연출을 넣기 전 첫 화면은 잘라낸다
        subprocess.run([ff, "-y", "-loglevel", "error", *skip, "-i", str(p), "-vf", vf, "-c:v", "libx264", "-preset", "slow",
                        "-crf", "20", "-pix_fmt", "yuv420p", str(o)], check=True)
        mp4s.append(o)
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{m.as_posix()}'\n" for m in mp4s), encoding="utf-8")
    final = out / "제주_같이나들이_데모.mp4"
    subprocess.run([ff, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(final)], check=True)
    print("완성", final, final.stat().st_size // 1024, "KB")
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
