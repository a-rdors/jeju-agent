// 버튼 아이콘(Streamlit 의 :material/...: 자리). 글자와 같은 색으로 그린다.
import { FILL, STROKE } from "@/lib/icons";

export default function Icon({ name }: { name: string }) {
  if (STROKE[name]) {
    return (
      <svg className="ic" viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none"
        stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
        <path d={STROKE[name]} />
      </svg>
    );
  }
  return (
    <svg className="ic" viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="currentColor">
      <path d={FILL[name] ?? FILL.info} />
    </svg>
  );
}
