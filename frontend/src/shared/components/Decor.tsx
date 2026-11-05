import { useEffect, useState } from 'react';
import {
  ArrowUp,
  BookOpen,
  FileText,
  Layers3,
  ScanLine,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';

export function PageArtwork({ variant = 'library' }: { variant?: string }) {
  const Icon =
    variant === 'images'
      ? ScanLine
      : variant === 'questions'
        ? Sparkles
        : variant === 'sources'
          ? ShieldCheck
          : variant === 'history'
            ? FileText
            : variant === 'symptoms'
              ? Layers3
              : BookOpen;
  return (
    <div className={'page-artwork art-' + variant} aria-hidden="true">
      <span className="page-art-ring" />
      <span className="page-art-ring outer" />
      <span className="page-art-sheet back" />
      <span className="page-art-sheet">
        <Icon size={34} />
        <span />
        <span />
        <span />
      </span>
      <span className="page-art-seal">
        <Sparkles size={19} />
      </span>
      <span className="page-art-dot one" />
      <span className="page-art-dot two" />
    </div>
  );
}
export function PageHeading({
  eyebrow,
  title,
  description,
  variant = 'library',
}: {
  eyebrow: string;
  title: string;
  description: string;
  variant?: string;
}) {
  return (
    <div className={'page-intro page-banner banner-' + variant}>
      <div className="page-banner-copy">
        <div className="eyebrow">
          <span />
          {eyebrow}
        </div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      <PageArtwork variant={variant} />
    </div>
  );
}
export function ReadingGuide() {
  return (
    <div className="reading-guide">
      <span>
        <BookOpen size={17} />
        Đọc nội dung
      </span>
      <i />
      <span>
        <ShieldCheck size={17} />
        Đối chiếu nguồn
      </span>
      <i />
      <span>
        <FileText size={17} />
        Lưu khi bạn muốn
      </span>
    </div>
  );
}
export function BackToTop() {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const update = () => setVisible(window.scrollY > 600);
    update();
    window.addEventListener('scroll', update, { passive: true });
    return () => window.removeEventListener('scroll', update);
  }, []);
  return visible ? (
    <button
      className="back-to-top"
      aria-label="Lên đầu trang"
      onClick={() =>
        window.scrollTo({
          top: 0,
          behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches
            ? 'instant'
            : 'smooth',
        })
      }
    >
      <ArrowUp size={20} />
    </button>
  ) : null;
}
