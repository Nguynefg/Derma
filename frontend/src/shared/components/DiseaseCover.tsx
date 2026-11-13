import { useState } from 'react';
import { ImageOff } from 'lucide-react';
import covers from '../data/diseaseCovers.json';

const normalize = (value: string) => value.trim().toLocaleLowerCase('en').replace(/\s+/g, ' ');
const coverByName = new Map(
  covers.flatMap((cover) => cover.names.map((name) => [normalize(name), cover] as const)),
);
export function findDiseaseCover(englishName?: string, name?: string) {
  return (englishName ? coverByName.get(normalize(englishName)) : undefined)
    ?? (name ? coverByName.get(normalize(name)) : undefined);
}

export function DiseaseCover({ name, englishName }: { name: string; englishName?: string }) {
  const cover = findDiseaseCover(englishName, name);
  const [failedSource, setFailedSource] = useState('');
  if (!cover || failedSource === cover.src)
    return (
      <div
        className="disease-cover-placeholder"
        role="img"
        aria-label={`${name}: chưa có ảnh riêng`}
      >
        <ImageOff size={30} aria-hidden="true" />
        <span>Chưa có ảnh riêng</span>
        <small>{name}</small>
      </div>
    );
  return (
    <div className="disease-cover">
      <img
        src={cover.src}
        alt={cover.src.startsWith('/assets/library/illustrations/') ? `${name} — minh họa` : name}
        loading="lazy"
        decoding="async"
        width={960}
        height={540}
        onError={() => setFailedSource(cover.src)}
      />
    </div>
  );
}
