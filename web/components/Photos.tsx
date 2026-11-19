"use client";
// 패널의 현장 사진: 제주데이터허브 무장애여행 조사 자료에서 뽑은 사진(장소마다 최대 3장).
// 누르면 크게 본다. 사진이 없는 장소는 아무것도 그리지 않는다.
import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { urls, type PlaceDot } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import Icon from "./Icon";

export function usePlacePhotos(place: string): string[] {
  const places = useApi<PlaceDot[]>(urls.places);
  return places.data?.find((p) => p.place === place)?.photos ?? [];
}

export default function PlacePhotos({ place }: { place: string }) {
  const photos = usePlacePhotos(place);
  const [open, setOpen] = useState<number | null>(null);
  if (!photos.length) return null;
  return (
    <>
      <div className={`photos n${Math.min(photos.length, 3)}`}>
        {photos.slice(0, 3).map((src, i) => (
          <button key={src} type="button" onClick={() => setOpen(i)} aria-label={`${place} 현장 사진 ${i + 1} 크게 보기`}>
            {/* eslint-disable-next-line @next/next/no-img-element -- public 폴더의 작은 JPEG 라 next/image 최적화가 필요 없다 */}
            <img src={src} alt="" loading="lazy" />
          </button>
        ))}
      </div>
      {open !== null && <Lightbox place={place} photos={photos} at={open} onMove={setOpen} onClose={() => setOpen(null)} />}
    </>
  );
}

function Lightbox({ place, photos, at, onMove, onClose }: {
  place: string; photos: string[]; at: number; onMove: (i: number) => void; onClose: () => void;
}) {
  const n = photos.length;
  const go = (d: number) => onMove((at + d + n) % n);
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      else if (e.key === "ArrowRight") onMove((at + 1) % n);
      else if (e.key === "ArrowLeft") onMove((at - 1 + n) % n);
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [at, n, onMove, onClose]);

  // 패널은 backdrop-filter 때문에 fixed 위치의 기준이 되므로 body 에 바로 그린다
  return createPortal(
    <div className="lightbox" role="dialog" aria-modal="true" aria-label={`${place} 현장 사진`} onClick={onClose}>
      <figure onClick={(e) => e.stopPropagation()}>
        {/* eslint-disable-next-line @next/next/no-img-element -- public 폴더의 작은 JPEG */}
        <img src={photos[at]} alt={`${place} 현장 사진 ${at + 1}`} />
        <figcaption>
          <span>{place} · {at + 1}/{n}</span>
          <small>사진: 제주데이터허브 무장애여행 정보</small>
        </figcaption>
      </figure>
      {n > 1 && (
        <>
          <button type="button" className="lb-nav prev" onClick={(e) => { e.stopPropagation(); go(-1); }} aria-label="이전 사진">
            <Icon name="arrow_back" />
          </button>
          <button type="button" className="lb-nav next" onClick={(e) => { e.stopPropagation(); go(1); }} aria-label="다음 사진">
            <Icon name="arrow_forward" />
          </button>
        </>
      )}
      <button type="button" className="lb-close" onClick={onClose} aria-label="사진 닫기" autoFocus>
        <Icon name="close" />
      </button>
    </div>,
    document.body,
  );
}
