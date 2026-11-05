import { AccountManager } from './components/AccountManager';
import React, { useEffect, useState } from 'react';
import { ArrowLeft, ArrowRight, Check, History, LockKeyhole, Pencil, Plus } from 'lucide-react';
import { api } from '../../shared/api/api';
import type { Disease, Symptom, User } from '../../shared/types/index';
import { formatDate } from '../../shared/utils/date';
import { Modal } from '../../shared/components/Modal';
import { Heading } from '../../shared/components/Heading';
import { ImageModelSummary } from '../images/components/ImageModelSummary';
import { DocumentManager } from './components/DocumentManager';
import { ImageArchive } from '../images/components/ImageArchive';

type EditForm = {
  name: string;
  english_name: string;
  category: string;
  summary: string;
  details: string;
  risk_factors: string;
  prevention: string;
  published: boolean;
  symptom_ids: string[];
  source_title: string;
  source_url: string;
};
const blank: EditForm = {
  name: '',
  english_name: '',
  category: 'Viêm da',
  summary: '',
  details: '',
  risk_factors: '',
  prevention: '',
  published: false,
  symptom_ids: [],
  source_title: '',
  source_url: '',
};
type AdminEntry = Pick<
  Disease,
  'id' | 'code' | 'name' | 'english_name' | 'category' | 'published' | 'review_status' | 'version'
>;
type LibraryResults = {
  items: AdminEntry[];
  total: number;
  total_all: number;
  categories: { value: string; label: string }[];
};
export function AdminPage({
  user,
  auth,
  symptoms,
  refresh,
  toast,
}: {
  user: User | null;
  auth: () => void;
  symptoms: Symptom[];
  refresh: () => Promise<void>;
  toast: (s: string) => void;
}) {
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [page, setPage] = useState(1);
  const [revision, setRevision] = useState(0);
  const [listBusy, setListBusy] = useState(false);
  const [editLoading, setEditLoading] = useState<string | null>(null);
  const [content, setContent] = useState<LibraryResults>({
    items: [],
    total: 0,
    total_all: 0,
    categories: [],
  });
  const pageSize = 25;
  const [items, setItems] = useState<Disease[]>([]),
    [stats, setStats] = useState<Record<string, number>>({}),
    [error, setError] = useState(''),
    [editing, setEditing] = useState<string | null>(null),
    [form, setForm] = useState<EditForm>(blank),
    [busy, setBusy] = useState(false),
    [logs, setLogs] = useState<
      { id: string; action: string; entity_id: string; created_at: string }[]
    >([]);
  useEffect(() => {
    setPage(1);
  }, [query, statusFilter, categoryFilter]);
  useEffect(() => {
    if (user?.role !== 'admin') return;
    const controller = new AbortController();
    setListBusy(true);
    const timer = window.setTimeout(() => {
      api<LibraryResults>(
        '/admin/library?' +
          new URLSearchParams({
            q: query,
            status: statusFilter,
            category: categoryFilter,
            page: String(page),
            page_size: String(pageSize),
          }),
        { signal: controller.signal },
      )
        .then((result) => {
          if (!controller.signal.aborted) setContent(result);
        })
        .catch((e) => {
          if (!controller.signal.aborted) setError(e.message);
        })
        .finally(() => {
          if (!controller.signal.aborted) setListBusy(false);
        });
    }, 250);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [user, query, statusFilter, categoryFilter, page, revision]);
  const load = async () => {
    try {
      const [d, s, l] = await Promise.all([
        api<Disease[]>('/admin/diseases'),
        api<Record<string, number>>('/admin/statistics'),
        api<typeof logs>('/admin/audit-logs'),
      ]);
      setItems(d);
      setStats(s);
      setLogs(l);
      setRevision((n) => n + 1);
      setError('');
    } catch (e) {
      setError((e as Error).message);
    }
  };
  useEffect(() => {
    if (user?.role === 'admin') void load();
  }, [user]);
  const edit = async (entry?: AdminEntry) => {
    setError('');
    if (!entry) {
      setForm({ ...blank });
      setEditing('new');
      return;
    }
    setEditLoading(entry.id);
    let d: Disease;
    try {
      d = await api<Disease>('/admin/library/' + entry.id);
    } catch (e) {
      setError((e as Error).message);
      return;
    } finally {
      setEditLoading(null);
    }
    const r = d.references.find((r) => r.slug?.startsWith('editor-')) || d.references[0];
    setForm({
      name: d.name,
      english_name: d.english_name,
      category: d.category,
      summary: d.summary,
      details: d.details,
      risk_factors: d.risk_factors,
      prevention: d.prevention,
      published: d.published,
      symptom_ids: d.symptoms.map((s) => s.id),
      source_title: r?.title || '',
      source_url: r?.url || '',
    });
    setEditing(d.id);
  };
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await api('/admin/diseases' + (editing === 'new' ? '' : '/' + editing), {
        method: editing === 'new' ? 'POST' : 'PUT',
        body: JSON.stringify(form),
      });
      setEditing(null);
      await load();
      toast('Đã lưu nội dung và nhật ký thay đổi.');
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const fieldLimits: Record<string, [number, number]> = {
    name: [2, 120],
    english_name: [2, 120],
    category: [2, 60],
    summary: [10, 2000],
    details: [10, 8000],
    risk_factors: [2, 3000],
    prevention: [2, 3000],
    source_title: [3, 200],
    source_url: [1, 1000],
  };
  const field = (name: keyof EditForm, label: string, multi = false) => (
    <label>
      {label}
      {multi ? (
        <textarea
          required
          value={String(form[name])}
          minLength={fieldLimits[name][0]}
          maxLength={fieldLimits[name][1]}
          onChange={(e) => setForm({ ...form, [name]: e.target.value })}
        />
      ) : (
        <input
          required
          type={name === 'source_url' ? 'url' : 'text'}
          minLength={fieldLimits[name][0]}
          maxLength={fieldLimits[name][1]}
          pattern={name === 'source_url' ? 'https://.+' : undefined}
          title={name === 'source_url' ? 'Nhập đường dẫn nguồn bắt đầu bằng https://' : undefined}
          value={String(form[name])}
          onChange={(e) => setForm({ ...form, [name]: e.target.value })}
        />
      )}
    </label>
  );
  return (
    <>
      <Heading
        eyebrow="QUẢN TRỊ"
        title="Chăm chút từng thông tin."
        description="Quản lý bài viết, nguồn tham khảo và theo dõi thay đổi."
      />
      {user?.role !== 'admin' ? (
        <div className="empty">
          <LockKeyhole size={35} />
          <h2>Khu vực quản trị nội dung</h2>
          <p>
            {user
              ? 'Tài khoản của bạn không có quyền quản trị.'
              : 'Đăng nhập bằng tài khoản quản trị để tiếp tục.'}
          </p>
          {!user && (
            <button className="button primary" onClick={auth}>
              Đăng nhập
            </button>
          )}
        </div>
      ) : (
        <>
          {error && !editing && <div className="inline-note error">{error}</div>}
          <div className="stats-grid">
            {[
              ['articles', 'Nội dung thư viện'],
              ['users', 'Tài khoản'],
              ['saved_searches', 'Tra cứu đã lưu'],
              ['edits', 'Lần biên tập'],
            ].map(([k, l]) => (
              <div className="stat-card" key={k}>
                <span>{l}</span>
                <strong>
                  {k === 'articles' ? content.total_all.toLocaleString('vi-VN') : (stats[k] ?? '—')}
                </strong>
              </div>
            ))}
          </div>
          <div className="results-heading">
            <h2>Nội dung thư viện</h2>
            <button className="button primary" onClick={() => edit()}>
              <Plus size={16} />
              Thêm bài viết
            </button>
          </div>
          <div className="management-toolbar">
            <input
              aria-label="Tìm bài viết quản trị"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Tên bệnh, tên tiếng Anh hoặc mã bài…"
            />
            <select
              aria-label="Lọc trạng thái bài"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">Mọi trạng thái</option>
              <option value="published">Đã xuất bản</option>
              <option value="draft">Bản nháp</option>
              <option value="pending">Chưa biên soạn</option>
            </select>
            <select
              aria-label="Lọc nhóm bài"
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
            >
              <option value="">Mọi nhóm bệnh</option>
              {content.categories.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
            <span className="muted">
              {listBusy
                ? 'Đang tải…'
                : `${content.total.toLocaleString('vi-VN')}/${content.total_all.toLocaleString('vi-VN')} nội dung`}
            </span>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Bài viết</th>
                  <th>Nhóm</th>
                  <th>Trạng thái</th>
                  <th>Phiên bản</th>
                  <th>Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {!listBusy &&
                  content.items.map((d) => (
                    <tr key={d.id}>
                      <td>
                        <strong>{d.name}</strong>
                        <small>{d.code}</small>
                        <small>{d.english_name}</small>
                      </td>
                      <td>{d.category}</td>
                      <td>
                        <span className={'state-badge ' + (!d.published ? 'draft' : '')}>
                          {d.review_status === 'pending'
                            ? 'Chưa biên soạn'
                            : d.published
                              ? 'Đã xuất bản'
                              : 'Bản nháp'}
                        </span>
                      </td>
                      <td>v{d.version}</td>
                      <td>
                        <button
                          className="text-button"
                          disabled={editLoading !== null}
                          onClick={() => void edit(d)}
                        >
                          <Pencil size={15} />
                          {editLoading === d.id ? 'Đang mở…' : 'Sửa'}
                        </button>
                      </td>
                    </tr>
                  ))}
                {listBusy && (
                  <tr>
                    <td colSpan={5}>Đang tải nội dung thư viện…</td>
                  </tr>
                )}
                {!listBusy && !content.items.length && (
                  <tr>
                    <td colSpan={5}>Không có nội dung phù hợp với bộ lọc.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          {content.total > pageSize && (
            <nav className="pagination" aria-label="Phân trang quản trị nội dung">
              <button disabled={listBusy || page === 1} onClick={() => setPage(page - 1)}>
                <ArrowLeft size={16} /> Trước
              </button>
              <span>
                Trang {page} / {Math.ceil(content.total / pageSize)}
              </span>
              <button
                disabled={listBusy || page * pageSize >= content.total}
                onClick={() => setPage(page + 1)}
              >
                Sau <ArrowRight size={16} />
              </button>
            </nav>
          )}
          <div className="admin-bottom">
            <div className="panel">
              <ImageModelSummary />
            </div>
            <div className="panel">
              <h3>
                <History size={18} />
                Nhật ký quản trị
              </h3>
              {!logs.length ? (
                <p className="muted">Chưa có thay đổi nội dung.</p>
              ) : (
                logs.slice(0, 5).map((l) => (
                  <p className="audit-line" key={l.id}>
                    <span>
                      {l.action === 'create' ? 'Thêm' : 'Sửa'} ·{' '}
                      {l.action === 'account_update'
                        ? `Tài khoản #${l.entity_id}`
                        : l.action === 'image_label'
                          ? `Nhãn ảnh #${l.entity_id}`
                          : l.action.startsWith('document_')
                            ? `Tài liệu #${l.entity_id}`
                            : items.find((d) => d.id === l.entity_id)?.name || l.entity_id}
                    </span>
                    <small>{formatDate(l.created_at)}</small>
                  </p>
                ))
              )}
            </div>
          </div>
          {user && <AccountManager currentUser={user} toast={toast} />}
          <DocumentManager diseases={items} toast={toast} />
          <ImageArchive admin diseases={items} />
        </>
      )}
      {editing && (
        <Modal
          title={editing === 'new' ? 'Thêm bài viết' : 'Biên tập bài viết'}
          onClose={() => {
            if (!busy) setEditing(null);
          }}
          wide
        >
          <form className="auth-form editor-form" onSubmit={submit}>
            <div className="form-grid">
              {field('name', 'Tên tiếng Việt')}
              {field('english_name', 'Tên tiếng Anh')}
            </div>
            {field('category', 'Nhóm chủ đề')}
            {field('summary', 'Tóm tắt', true)}
            {field('details', 'Tổng quan', true)}
            {field('risk_factors', 'Yếu tố liên quan', true)}
            {field('prevention', 'Phòng ngừa & chăm sóc', true)}
            <label>Triệu chứng liên quan</label>
            <div className="chips">
              {symptoms.map((s) => (
                <button
                  type="button"
                  className={'filter-chip ' + (form.symptom_ids.includes(s.id) ? 'selected' : '')}
                  key={s.id}
                  onClick={() =>
                    setForm({
                      ...form,
                      symptom_ids: form.symptom_ids.includes(s.id)
                        ? form.symptom_ids.filter((x) => x !== s.id)
                        : [...form.symptom_ids, s.id],
                    })
                  }
                >
                  {s.name}
                </button>
              ))}
            </div>
            {field('source_title', 'Tên tài liệu nguồn')}
            {field('source_url', 'Liên kết nguồn (HTTPS)')}
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={form.published}
                onChange={(e) => setForm({ ...form, published: e.target.checked })}
              />
              Xuất bản bài viết sau khi lưu
            </label>
            <p className="muted">
              Biên tập viên chịu trách nhiệm kiểm tra nguồn và quyền sử dụng. Biên tập không tương
              đương thẩm định lâm sàng.
            </p>
            <div className="editor-actions">
              {error && (
                <p className="error-text" role="alert">
                  {error}
                </p>
              )}
              <button
                className="button secondary"
                type="button"
                disabled={busy}
                onClick={() => setEditing(null)}
              >
                Hủy
              </button>
              <button className="button primary" disabled={busy}>
                {busy ? 'Đang lưu…' : 'Lưu bài viết'}
                <Check size={17} />
              </button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}
