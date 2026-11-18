// 화면 조각. app/ui.py 의 HTML 도우미(verdict, tiles, notes, timeline, checks, shop ...)를 React 로 옮겼다.
import type { CSSProperties, ReactNode } from "react";
import { ART, ICON, dataUri } from "@/lib/art";
import type { Check, CoursePoint } from "@/lib/api";
import Icon from "./Icon";

const VERDICT: Record<string, [string, string]> = {
  green: ["leaf", "check"],
  orange: ["sea", "people"],
  gray: ["stone", "question"],
};

/** svg 그림을 <img>로. alt 가 없으면 꾸밈 그림으로 숨긴다. */
export function Svg({ src, className, alt, style }: { src: string; className?: string; alt?: string; style?: CSSProperties }) {
  return (
    // eslint-disable-next-line @next/next/no-img-element -- 직접 만든 SVG data URI 라 next/image 최적화가 필요 없다
    <img className={className} src={src} alt={alt ?? ""} aria-hidden={alt ? undefined : true} style={style} />
  );
}

export function Avatar() {
  return (
    <div className="avatar">
      <Svg src={ART.harFace} />
    </div>
  );
}

export function DashHead({ tag, note = "" }: { tag: string; note?: string }) {
  return (
    <div className="dash-head">
      <b>{tag}</b>
      <span>{note}</span>
    </div>
  );
}

export function Verdict({ color, label, reason }: { color: string; label: string; reason: string }) {
  const [cls, icon] = VERDICT[color] ?? ["stone", "question"];
  return (
    <div className={`verdict ${cls}`}>
      <div className="vi">
        <Svg src={dataUri(ICON[icon])} />
      </div>
      <div>
        <div className="vl">{label}</div>
        <div className="vr">{reason}</div>
      </div>
    </div>
  );
}

export function PlaceHead({ name, where }: { name: string; where: string }) {
  return (
    <div className="place-head">
      <h2 className="place-name">{name}</h2>
      <div className="place-where">{where}</div>
    </div>
  );
}

/** items: [제목, 값, 'yes'|'no'|''] */
export function Tiles({ items }: { items: [string, string, string][] }) {
  return (
    <div className="tiles">
      {items.map(([k, v, st]) => (
        <div key={k} className={`tile ${st}`}>
          <small>{k}</small>
          <b>{v}</b>
        </div>
      ))}
    </div>
  );
}

export function Notes({ good, warn }: { good: string[]; warn: string[] }) {
  if (!good.length && !warn.length) return null;
  return (
    <ul className="notes">
      {good.map((g, i) => (
        <li key={`g${i}`} className="good"><i aria-hidden="true">✓</i><span>{g}</span></li>
      ))}
      {warn.map((w, i) => (
        <li key={`w${i}`} className="warn"><i aria-hidden="true">!</i><span><span className="sr-only">주의: </span>{w}</span></li>
      ))}
    </ul>
  );
}

export function WeatherBox({ line, tips }: { line: string; tips: string[] }) {
  return (
    <div className="weather">
      <span aria-hidden="true">☂</span>
      <div>
        {tips.length > 0 && (
          <>
            <b>{tips.map((t, i) => (<span key={i}>{i > 0 && <br />}{t}</span>))}</b>
            <br />
          </>
        )}
        <span>{line}</span>
      </div>
    </div>
  );
}

export function Sect({ children }: { children: ReactNode }) {
  return <h3 className="sect">{children}</h3>;
}

export function Checks({ rows }: { rows: Check[] }) {
  return (
    <div className="checks">
      {rows.map((c) => (
        <div key={c.item}>
          <b>{c.item}</b>
          <span>{c.status}</span>
          <span className={`pill ${c.known ? "ok" : "no"}`}>{c.known ? "확인됨" : "확인 안 됨"}</span>
        </div>
      ))}
    </div>
  );
}

export function Timeline({ points, notCaution }: { points: CoursePoint[]; notCaution: Set<string> }) {
  return (
    <ul className="timeline">
      {points.map((p, i) => {
        const caution = p.flags.some((f) => !notCaution.has(f));
        return (
          <li key={i} className={caution ? "caution" : ""}>
            <div className="m">{caution && <span className="sr-only">확인할 지점, </span>}출발 후 약 {p.at_m}m</div>
            <div className="t">{p.label}</div>
            <div className="f">{p.flags.map((f) => <span key={f}>{f}</span>)}</div>
          </li>
        );
      })}
    </ul>
  );
}

/** tags: [글자, 'wc'|'gray'|'red'|''] */
export function Shop({ name, meta, tags }: { name: string; meta: string; tags: [string, string][] }) {
  return (
    <div className="shop">
      <b>{name}</b>
      <div className="meta">{meta}</div>
      {tags.length > 0 && (
        <div className="tags">
          {tags.map(([x, c], i) => <span key={i} className={`tag ${c}`}>{x}</span>)}
        </div>
      )}
    </div>
  );
}

export function Src({ children }: { children: ReactNode }) {
  return <div className="src">{children}</div>;
}

export function Info({ children }: { children: ReactNode }) {
  return (
    <div className="info" role="note">
      <Icon name="info" />
      <div>{children}</div>
    </div>
  );
}

export function Caption({ children }: { children: ReactNode }) {
  return <p className="caption">{children}</p>;
}

export function Loading({ text = "불러오는 중이에요" }: { text?: string }) {
  return (
    <div className="loading" role="status">
      <span className="dots" aria-hidden="true"><i /><i /><i /></span>
      {text}
    </div>
  );
}

/** 바깥 링크 버튼(길안내·전화). */
export function LinkButton({ href, icon, kind = "secondary", block, children }:
  { href: string; icon: string; kind?: "primary" | "secondary"; block?: boolean; children: ReactNode }) {
  const external = href.startsWith("http");
  return (
    <a className={`btn btn-${kind}${block ? " btn-block" : ""}`} href={href}
      {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}>
      <Icon name={icon} />
      <span>{children}</span>
      {external && <span className="sr-only"> (새 창)</span>}
    </a>
  );
}
