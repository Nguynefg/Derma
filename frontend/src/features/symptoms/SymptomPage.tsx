import { useState } from 'react';
import {
  Activity,
  ArrowDown,
  ArrowUpRight,
  Brain,
  Check,
  HeartPulse,
  LoaderCircle,
  Plus,
  Search,
  ShieldCheck,
  Sparkles,
  X,
} from 'lucide-react';
import { api } from '../../shared/api/api';
import type { Disease, Symptom, User, SearchResult } from '../../shared/types/index';
import { SaveButton } from '../profile/components/SaveButton';
import { DiseaseCard } from '../library/components/DiseaseCard';

export function SymptomPage({
  symptoms,
  open,
  user,
  auth,
  toast,
}: {
  symptoms: Symptom[];
  open: (d: Disease) => void;
  user: User | null;
  auth: () => void;
  toast: (s: string) => void;
}) {
  const [chosen, setChosen] = useState<string[]>([]),
    [items, setItems] = useState<Disease[] | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(''),
    [lastQuery, setLastQuery] = useState('');
  const [specialty, setSpecialty] = useState('');
  const [filter, setFilter] = useState('');
  const specialties = [...new Set(symptoms.flatMap((s) => s.specialties || []))].sort((a, b) =>
    a.localeCompare(b, 'vi'),
  );
  const norm = (s: string) =>
    s
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/đ/g, 'd');
  const visibleSymptoms = symptoms.filter(
    (s) =>
      (!specialty || s.specialties?.includes(specialty)) && norm(s.name).includes(norm(filter)),
  );
  const selectSpecialty = (value: string) => {
    setSpecialty(value);
    setItems(null);
    setError('');
  };
  const toggle = (id: string) => {
    setChosen((v) => (v.includes(id) ? v.filter((i) => i !== id) : [...v, id]));
    setItems(null);
    setError('');
  };
  const submit = async () => {
    setBusy(true);
    setError('');
    try {
      const r = await api<SearchResult>('/search/symptoms', {
        method: 'POST',
        body: JSON.stringify({
          symptoms: chosen.map((id) => ({ id, presence: 'present' })),
          specialty,
        }),
      });
      setItems(r.items);
      setLastQuery(
        symptoms
          .filter((s) => chosen.includes(s.id))
          .map((s) => s.name)
          .join(', '),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <section className="symptom-studio-hero">
        <div className="symptom-hero-copy">
          <span className="symptom-eyebrow">
            <span /> KHÁM PHÁ TỪ TRIỆU CHỨNG
          </span>
          <h1>
            Lắng nghe cơ thể.
            <br />
            <em>Tìm hiểu rõ hơn.</em>
          </h1>
          <p>
            Từ những dấu hiệu nhỏ, tìm đến thông tin bạn cần. Chọn điều bạn đang cảm nhận để khám
            phá các bài viết liên quan.
          </p>
          <a href="#symptom-explorer" className="symptom-hero-link">
            Bắt đầu khám phá <ArrowDown size={17} />
          </a>
          <div className="symptom-hero-metrics">
            <span>
              <strong>{symptoms.length}</strong> dấu hiệu trong thư viện
            </span>
            <i />
            <span>
              <strong>{specialties.length}</strong> chuyên khoa
            </span>
          </div>
        </div>
        <div className="symptom-orbit" aria-hidden="true">
          <div className="symptom-orbit-ring" />
          <div className="symptom-orbit-ring inner" />
          <div className="symptom-orbit-core">
            <HeartPulse size={62} strokeWidth={1.3} />
          </div>
          <span className="symptom-orbit-badge brain">
            <Brain size={25} />
          </span>
          <span className="symptom-orbit-badge activity">
            <Activity size={25} />
          </span>
          <span className="symptom-orbit-badge spark">
            <Sparkles size={23} />
          </span>
          <div className="symptom-orbit-caption">
            <span /> Mỗi dấu hiệu, một điểm bắt đầu
          </div>
        </div>
      </section>
      <div className="symptom-journey">
        <span>
          <b>01</b> Nhận biết dấu hiệu
        </span>
        <i />
        <span>
          <b>02</b> Tìm nội dung phù hợp
        </span>
        <i />
        <span>
          <b>03</b> Hiểu thêm về sức khỏe <ArrowUpRight size={16} />
        </span>
      </div>
      <div className="symptom-layout symptom-workspace">
        <section className="panel symptom-picker" id="symptom-explorer">
          <div className="symptom-section-kicker">
            <Activity size={15} /> BỘ KHÁM PHÁ TRIỆU CHỨNG
          </div>
          <div className="step-label">Bạn đang cảm thấy thế nào?</div>
          <p className="muted">
            Chọn một hoặc nhiều dấu hiệu. Bạn có thể thay đổi lựa chọn bất cứ lúc nào.
          </p>
          <div className="symptom-filters">
            <label className="symptom-search-field">
              <Search size={20} aria-hidden="true" />
              <input
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                placeholder="Tìm nhanh: đau đầu, ho, ngứa…"
                aria-label="Tìm dấu hiệu"
              />
              {filter && (
                <button onClick={() => setFilter('')} aria-label="Xóa từ tìm kiếm">
                  <X size={16} />
                </button>
              )}
            </label>
          </div>
          <div className="symptom-filter-caption">Lọc theo chuyên khoa</div>
          <div className="symptom-specialty-tabs" role="group" aria-label="Lọc theo chuyên khoa">
            <button
              disabled={busy}
              aria-pressed={!specialty}
              className={!specialty ? 'active' : ''}
              onClick={() => selectSpecialty('')}
            >
              Tất cả <span>{symptoms.length}</span>
            </button>
            {specialties.map((s) => (
              <button
                key={s}
                disabled={busy}
                aria-pressed={specialty === s}
                className={specialty === s ? 'active' : ''}
                onClick={() => selectSpecialty(s)}
              >
                {s}
              </button>
            ))}
          </div>
          <div className="symptom-list-heading">
            <strong>{specialty || 'Tất cả dấu hiệu'}</strong>
            <span>{visibleSymptoms.length} dấu hiệu</span>
          </div>
          <div className="symptom-choices" role="group" aria-label="Chọn các triệu chứng đang có">
            {visibleSymptoms.map((s) => (
              <button
                disabled={busy || (!chosen.includes(s.id) && chosen.length >= 30)}
                key={s.id}
                className={'symptom-option ' + (chosen.includes(s.id) ? 'checked' : '')}
                aria-pressed={chosen.includes(s.id)}
                onClick={() => toggle(s.id)}
              >
                <span className="symptom-choice-icon" aria-hidden="true">
                  {chosen.includes(s.id) ? <Check size={20} /> : <Activity size={20} />}
                </span>
                <span className="symptom-choice-copy">
                  <strong>{s.name}</strong>
                  <small>{s.specialties?.join(' · ') || 'Dấu hiệu sức khỏe'}</small>
                </span>
                <span className="symptom-choice-action" aria-hidden="true">
                  {chosen.includes(s.id) ? <Check size={16} /> : <Plus size={16} />}
                </span>
              </button>
            ))}
          </div>
          {!visibleSymptoms.length && <p className="muted">Không có dấu hiệu phù hợp bộ lọc.</p>}
          <p className="symptom-limit-note">
            Chọn tối đa 30 dấu hiệu phù hợp với tình trạng của bạn.
          </p>
        </section>
        <aside className="symptom-summary panel">
          <div className="symptom-summary-masthead">
            <span>
              <Sparkles size={15} /> GÓC TRA CỨU CỦA BẠN
            </span>
            <div className="symptom-selection-number">
              {String(chosen.length).padStart(2, '0')}
              <small>dấu hiệu đã chọn</small>
            </div>
          </div>
          <div className="step-label">Lựa chọn của bạn</div>
          <div className="symptom-selection-heading">
            <span aria-live="polite">{chosen.length}/30 dấu hiệu</span>
            {!!chosen.length && (
              <button
                className="symptom-clear"
                disabled={busy}
                onClick={() => {
                  setChosen([]);
                  setItems(null);
                  setError('');
                }}
              >
                Bỏ chọn tất cả
              </button>
            )}
          </div>
          <div className="symptom-selected-list">
            {chosen.length ? (
              symptoms
                .filter((s) => chosen.includes(s.id))
                .map((s) => (
                  <button
                    key={s.id}
                    disabled={busy}
                    onClick={() => toggle(s.id)}
                    aria-label={'Bỏ chọn ' + s.name}
                  >
                    {s.name}
                    <X size={15} aria-hidden="true" />
                  </button>
                ))
            ) : (
              <div className="symptom-selection-empty">
                <HeartPulse size={30} aria-hidden="true" />
                <strong>Bắt đầu từ một dấu hiệu</strong>
                <p>Chọn trong danh sách để bắt đầu tìm các bài viết liên quan.</p>
              </div>
            )}
          </div>
          <button
            className="button primary symptom-search-button"
            disabled={!chosen.length || busy}
            onClick={submit}
          >
            {busy ? <LoaderCircle className="spin" size={18} /> : <Search size={18} />}
            {busy ? 'Đang tìm kiếm…' : 'Tìm bài viết liên quan'}
          </button>
          {error && (
            <p className="error-text" role="alert">
              {error}
            </p>
          )}
          <div className="symptom-result-note">
            <ShieldCheck size={20} />
            <p>
              Kết quả là các bài viết có nhắc đến dấu hiệu đã chọn, không phải kết luận chẩn đoán.
            </p>
          </div>
        </aside>
      </div>
      {items && (
        <section className="results-section">
          <div className="results-heading">
            <h2>{items.length} chủ đề liên quan</h2>
            <SaveButton
              user={user}
              auth={auth}
              toast={toast}
              mode="symptom"
              query={lastQuery}
              items={items}
            />
          </div>
          {items.length ? (
            <div className="disease-grid">
              {items.map((d, i) => (
                <DiseaseCard key={d.id} disease={d} index={i} open={() => open(d)} />
              ))}
            </div>
          ) : (
            <div className="empty">
              <p>Kho dữ liệu hiện tại chưa có chủ đề khớp.</p>
            </div>
          )}
        </section>
      )}
    </>
  );
}
