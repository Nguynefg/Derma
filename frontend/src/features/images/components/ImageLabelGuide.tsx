import { useEffect, useState } from 'react';
import { Search } from 'lucide-react';
import { api } from '../../../shared/api/api';

export type ImageObservations = { site: string; label_ids: string[] };
type Catalog = {
  labels: { id: string; name: string }[];
  sites: { id: string; name: string }[];
  topics: {
    id: string;
    name: string;
    english_name: string;
    category: string;
    scope: { code: string; name: string; note: string };
  }[];
  notice: string;
};
const normalize = (s: string) =>
  s
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd');

export function ImageLabelGuide({
  value,
  onChange,
  disabled,
  open,
}: {
  value: ImageObservations;
  onChange: (v: ImageObservations) => void;
  disabled: boolean;
  open: (id: string) => void;
}) {
  const [data, setData] = useState<Catalog | null>(null);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('');
  const [limit, setLimit] = useState(8);
  useEffect(() => {
    const controller = new AbortController();
    setError('');
    api<Catalog>('/images/labels', { signal: controller.signal })
      .then((r) => {
        if (!controller.signal.aborted) setData(r);
      })
      .catch((e) => {
        if (!controller.signal.aborted)
          setError(
            (e as Error).message === 'Not Found'
              ? 'Chưa tải được danh mục nhãn. Vui lòng tải lại sau.'
              : (e as Error).message,
          );
      });
    return () => controller.abort();
  }, [attempt]);
  const topics = (data?.topics || []).filter(
    (t) =>
      (!category || t.category === category) &&
      normalize(t.name + ' ' + t.english_name).includes(normalize(query.trim())),
  );
  return (
    <div className="image-label-guide">
      <details className="image-label-details">
        <summary>
          Dấu hiệu bổ sung{' '}
          <span>
            {value.label_ids.length ? `${value.label_ids.length} nhãn đã chọn` : 'Không bắt buộc'}
          </span>
        </summary>
        <p className="muted">
          Chọn những dấu hiệu bạn nhận thấy, tối đa 8 nhãn. Đây là thông tin bạn cung cấp, không
          phải kết luận bệnh.
        </p>
        {data && (
          <fieldset disabled={disabled}>
            <label className="image-site-label">
              Vị trí vùng ảnh
              <select
                value={value.site}
                onChange={(e) => onChange({ ...value, site: e.target.value })}
              >
                {data.sites.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </label>
            <div className="image-label-chips">
              {data.labels.map((l) => {
                const checked = value.label_ids.includes(l.id);
                return (
                  <button
                    type="button"
                    className={'filter-chip ' + (checked ? 'active' : '')}
                    key={l.id}
                    aria-pressed={checked}
                    disabled={disabled || (!checked && value.label_ids.length >= 8)}
                    onClick={() =>
                      onChange({
                        ...value,
                        label_ids: checked
                          ? value.label_ids.filter((id) => id !== l.id)
                          : [...value.label_ids, l.id],
                      })
                    }
                  >
                    {l.name}
                  </button>
                );
              })}
            </div>
            {(value.label_ids.length > 0 || value.site !== 'unspecified') && (
              <button
                type="button"
                className="text-button"
                onClick={() => onChange({ site: 'unspecified', label_ids: [] })}
              >
                Bỏ thông tin bổ sung
              </button>
            )}
          </fieldset>
        )}
      </details>
      <details className="image-label-details">
        <summary>
          Danh mục bệnh tham khảo qua ảnh{' '}
          <span>{data ? `${data.topics.length} chủ đề` : 'Đang tải…'}</span>
        </summary>
        <p className="muted">{data?.notice}</p>
        <div className="image-catalog-filters">
          <label>
            <Search size={16} />
            <input
              aria-label="Tìm bệnh trong danh mục ảnh"
              placeholder="Tên bệnh, ví dụ: nấm da đầu…"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setLimit(8);
              }}
            />
          </label>
          <select
            aria-label="Nhóm bệnh trong danh mục ảnh"
            value={category}
            onChange={(e) => {
              setCategory(e.target.value);
              setLimit(8);
            }}
          >
            <option value="">Tất cả nhóm</option>
            {[...new Set(data?.topics.map((t) => t.category))].sort().map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </div>
        <p className="muted">{topics.length} chủ đề phù hợp</p>
        <div className="image-catalog-list">
          {topics.slice(0, limit).map((t) => (
            <article key={t.id}>
              <button type="button" className="text-button" onClick={() => open(t.id)}>
                {t.name}
              </button>
              <small>{t.category}</small>
              <span className={'image-scope image-scope-' + t.scope.code}>{t.scope.name}</span>
              <p>{t.scope.note}</p>
            </article>
          ))}
        </div>
        {topics.length > limit && (
          <button
            type="button"
            className="button secondary full"
            onClick={() => setLimit((n) => n + 8)}
          >
            Xem thêm chủ đề
          </button>
        )}
      </details>
      {error && (
        <p className="error-text" role="alert">
          {error}{' '}
          <button type="button" className="text-button" onClick={() => setAttempt((n) => n + 1)}>
            Thử lại
          </button>
        </p>
      )}
    </div>
  );
}
