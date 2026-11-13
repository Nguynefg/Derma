import { DiseaseCover } from '../../shared/components/DiseaseCover';
import { useEffect, useRef, useState } from 'react';
import { ArrowLeft, ArrowRight, LoaderCircle, Search, LayoutGrid, List, SlidersHorizontal } from 'lucide-react';
import { api } from '../../shared/api/api';
import { libraryPresentation } from '../../shared/utils/libraryPresentation';
import { libraryArtwork } from '../../shared/utils/libraryArtwork';
import type { Disease, User } from '../../shared/types/index';
import { Heading } from '../../shared/components/Heading';
import { ICDDetailModal } from './components/ICDCatalog';
import { SaveButton } from '../profile/components/SaveButton';

type Entry = {
  id: string;
  type: 'article' | 'icd';
  title: string;
  code: string | null;
  category: string;
  summary: string;
  article?: Disease;
  icd?: { chapter?: string; chapter_title?: string; group_name?: string; original_title?: string };
};
type Results = { items: Entry[]; total: number; article_count: number; icd_count: number };
export function LibraryPage({
  initialQuery,
  initialSpecialty = '',
  all,
  open,
  user,
  auth,
  toast,
}: {
  initialQuery: string;
  initialSpecialty?: string;
  all: Disease[];
  open: (d: Disease) => void;
  user: User | null;
  auth: () => void;
  toast: (s: string) => void;
}) {
  const [q, setQ] = useState(initialQuery),
    [submitted, setSubmitted] = useState(initialQuery);
  const [specialty, setSpecialty] = useState(initialSpecialty),
    [category, setCategory] = useState(''),
    [symptom, setSymptom] = useState(''),
    [sort, setSort] = useState('name');
  const [view, setView] = useState<'cards' | 'list'>('cards');
  const [page, setPage] = useState(1),
    [retry, setRetry] = useState(0),
    [busy, setBusy] = useState(true),
    [error, setError] = useState('');
  const [data, setData] = useState<Results>({
    items: [],
    total: 0,
    article_count: 0,
    icd_count: 0,
  });
  const [chapters, setChapters] = useState<{ code: string; title: string }[]>([]);
  const [selectedIcd, setSelectedIcd] = useState<string | null>(null);
  const resultRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSubmitted(q.trim());
      setPage(1);
    }, 350);
    return () => window.clearTimeout(timer);
  }, [q]);
  const chapter = category.startsWith('chapter:')
    ? category.slice('chapter:'.length)
    : symptom === 'chapter:21'
      ? '21'
      : '';
  const categoryFilter = category.startsWith('chapter:') ? '' : category;
  const symptomFilter = symptom.startsWith('chapter:') ? '' : symptom;
  const specialties = [...new Set(all.map((d) => d.specialty).filter(Boolean))].sort((a, b) =>
    a.localeCompare(b, 'vi'),
  );
  const categories = [
    ...new Set(all.filter((d) => !specialty || d.specialty === specialty).map((d) => d.category)),
  ].sort((a, b) => a.localeCompare(b, 'vi'));
  const symptoms = [...new Map(all.flatMap((d) => d.symptoms).map((s) => [s.id, s])).values()].sort(
    (a, b) => a.name.localeCompare(b.name, 'vi'),
  );
  useEffect(() => {
    const c = new AbortController();
    api<{ chapters: { code: string; title: string }[] }>('/icd/summary', { signal: c.signal })
      .then((r) => {
        if (!c.signal.aborted) setChapters(r.chapters);
      })
      .catch(() => {});
    return () => c.abort();
  }, []);
  useEffect(() => {
    const c = new AbortController();
    setBusy(true);
    setError('');
    api<Results>(
      '/library/search?' +
        new URLSearchParams({
          q: submitted,
          content_type: 'all',
          specialty,
          category: categoryFilter,
          symptom: symptomFilter,
          chapter,
          sort,
          page: String(page),
          page_size: '12',
        }),
      { signal: c.signal },
    )
      .then((r) => {
        if (!c.signal.aborted) setData(r);
      })
      .catch((e) => {
        if (!c.signal.aborted)
          setError(
            e.message === 'Not Found'
              ? 'Máy chủ chưa tải thư viện mới. Vui lòng khởi động lại web.'
              : e.message,
          );
      })
      .finally(() => {
        if (!c.signal.aborted) setBusy(false);
      });
    return () => c.abort();
  }, [submitted, specialty, categoryFilter, symptomFilter, chapter, sort, page, retry]);
  const reset = () => {
    setQ('');
    setSubmitted('');
    setSpecialty('');
    setCategory('');
    setSymptom('');
    setSort('name');
    setPage(1);
  };
  const turn = (next: number) => {
    setPage(next);
    resultRef.current?.scrollIntoView({
      block: 'start',
      behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches
        ? 'instant'
        : 'smooth',
    });
  };
  const pages = Math.max(1, Math.ceil(data.total / 12));
  return (
    <section className="catalog-library">
      <Heading
        eyebrow="THƯ VIỆN SỨC KHỎE"
        title="Thư viện bệnh lý"
        description="Thông tin sức khỏe, được trình bày rõ ràng. Tra cứu theo tên, chuyên khoa hoặc dấu hiệu bạn quan tâm."
      />
      <form
        className="library-search"
        onSubmit={(e) => {
          e.preventDefault();
          setSubmitted(q.trim());
          setPage(1);
          setRetry((n) => n + 1);
        }}
      >
        <Search />
        <input
          aria-label="Tìm trong thư viện"
          placeholder="Tên bệnh tiếng Việt, tiếng Anh hoặc mã tra cứu…"
          maxLength={300}
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <button className="button primary">
          Tìm kiếm <ArrowRight size={16} />
        </button>
      </form>
      <div className="catalog-layout">
      <aside className="catalog-filters" aria-label="Bộ lọc thư viện">
      <details open>
        <summary><SlidersHorizontal size={17} /> Bộ lọc thư viện</summary>
        <p className="catalog-filter-caption">CHUYÊN KHOA</p>
      <div className="filter-row">
        {['', ...specialties].map((s) => (
          <button
            key={s}
            className={'filter-chip ' + (specialty === s ? 'selected' : '')}
            aria-pressed={specialty === s}
            onClick={() => {
              setSpecialty(s);
              setCategory('');
              setSymptom('');
              setPage(1);
            }}
          >
            {s || 'Tất cả chuyên khoa'}
          </button>
        ))}
      </div>
      <div className="management-toolbar library-tools">
        <label>
          Nhóm chủ đề
          <select
            value={category}
            onChange={(e) => {
              setCategory(e.target.value);
              if (symptom === 'chapter:21') setSymptom('');
              setPage(1);
            }}
          >
            <option value="">Tất cả nhóm</option>
            <optgroup label="Chủ đề thư viện">
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </optgroup>
            <optgroup label="Nhóm phân loại">
              {chapters
                .filter((c) => c.code !== '21')
                .map((c) => (
                  <option key={c.code} value={'chapter:' + c.code}>
                    {c.title}
                  </option>
                ))}
            </optgroup>
          </select>
        </label>
        <label>
          Dấu hiệu được đề cập
          <select
            value={symptom}
            onChange={(e) => {
              setSymptom(e.target.value);
              if (e.target.value === 'chapter:21') setCategory('');
              setPage(1);
            }}
          >
            <option value="">Tất cả dấu hiệu</option>
            {chapters.some((c) => c.code === '21') && (
              <option value="chapter:21">{chapters.find((c) => c.code === '21')?.title}</option>
            )}
            {symptoms.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Sắp xếp
          <select
            value={sort}
            onChange={(e) => {
              setSort(e.target.value);
              setPage(1);
            }}
          >
            <option value="name">Tên A–Z</option>
            <option value="updated">Cập nhật gần nhất</option>
          </select>
        </label>
        <button className="text-button" onClick={reset}>
          Xóa bộ lọc
        </button>
      </div>
      </details>
      </aside>
      <section className="catalog-results" aria-label="Nội dung thư viện">
      <div
        className="results-heading library-result-heading"
        ref={resultRef}
        role="status"
        aria-live="polite"
        aria-atomic="true"
      >
        <p>
          {busy ? (
            'Đang tìm…'
          ) : error ? (
            'Tra cứu chưa hoàn tất'
          ) : (
            <>
              <strong>{data.total.toLocaleString('vi-VN')}</strong> nội dung trong thư viện
              {data.total > 0 && (
                <small className="range-label">
                  {' '}
                  · Hiển thị {(page - 1) * 12 + 1}–{Math.min(page * 12, data.total)}
                </small>
              )}
            </>
          )}
        </p>
        <div className="catalog-view-switch" role="group" aria-label="Cách hiển thị thư viện">
          <button aria-label="Hiển thị dạng thẻ" aria-pressed={view === 'cards'} onClick={() => setView('cards')}><LayoutGrid size={18} /></button>
          <button aria-label="Hiển thị dạng danh sách" aria-pressed={view === 'list'} onClick={() => setView('list')}><List size={18} /></button>
        </div>
      </div>
      {!busy && !error && data.items.length > 0 && (
        <SaveButton user={user} auth={auth} toast={toast} mode="keyword"
          query={[submitted, specialty, category, symptom].filter(Boolean).join(' · ')}
          items={data.items.filter((item) => item.type === 'article').map((item) => ({ id: item.id }))} />
      )}
      {error ? (
        <div className="inline-note error">
          {error}
          <button className="button secondary" onClick={() => setRetry((n) => n + 1)}>
            Thử lại
          </button>
        </div>
      ) : busy ? (
        <div className="loading-state">
          <LoaderCircle className="spin" />
          Đang tìm trong thư viện…
        </div>
      ) : data.items.length ? (
        <>
          <div className={"unified-library-grid catalog-view-" + view}>
            {data.items.map((d) => {
              const presentation = libraryPresentation(d);
              const artwork = libraryArtwork(d, presentation.category);
              return (
                <article
                  className={`unified-library-card library-card-${artwork.theme}`}
                  key={d.id}
                  aria-labelledby={`library-title-${d.id}`}
                >
                  <DiseaseCover
                    name={d.title}
                    englishName={d.article?.english_name || d.icd?.original_title}
                  />
                  <div className="library-card-body">
                    <span className="library-card-group" title={artwork.groupTitle}>
                      {presentation.supplemental ? presentation.label : artwork.label}
                    </span>
                    {presentation.scientificName && (
                      <small className="muted">Tên theo danh pháp quốc tế</small>
                    )}
                    <button
                      className={`unified-card-title${d.title.split(/\s+/).some((word) => word.length > 32) ? ' library-card-long-title' : ''}`}
                      id={`library-title-${d.id}`}
                      title={presentation.title}
                      onClick={() => (d.article ? open(d.article) : setSelectedIcd(d.id))}
                    >
                      {presentation.title}
                    </button>
                    <p className={presentation.summaryPending ? 'library-card-pending' : undefined}>
                      {presentation.summary}
                    </p>
                    {presentation.summaryPending && !presentation.supplemental && (
                      <small className="muted">Chưa có bài tổng quan</small>
                    )}
                    <button
                      className="library-card-link"
                      onClick={() => (d.article ? open(d.article) : setSelectedIcd(d.id))}
                    >
                      Xem thông tin <ArrowRight size={16} />
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
          {pages > 1 && (
            <nav className="pagination" aria-label="Phân trang thư viện">
              <button disabled={page === 1} onClick={() => turn(page - 1)}>
                <ArrowLeft size={16} />
                Trước
              </button>
              <span>
                Trang {page} / {pages}
              </span>
              <button disabled={page >= pages} onClick={() => turn(page + 1)}>
                Sau
                <ArrowRight size={16} />
              </button>
            </nav>
          )}
        </>
      ) : (
        <div className="empty">
          <Search size={32} />
          <h2>Chưa có kết quả phù hợp</h2>
          <p>
            Thử tên tiếng Việt, tiếng Anh hoặc mã phân loại. Bộ lọc dấu hiệu chỉ trả nội dung đã có
            liên kết triệu chứng.
          </p>
          <button className="button secondary" onClick={reset}>
            Xem toàn bộ thư viện
          </button>
        </div>
      )}
      </section>
      </div>
      {selectedIcd && <ICDDetailModal id={selectedIcd} onClose={() => setSelectedIcd(null)} />}
    </section>
  );
}
