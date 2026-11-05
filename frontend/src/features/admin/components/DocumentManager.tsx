import React, { useEffect, useState } from 'react';
import { Check, ChevronDown, Plus, X } from 'lucide-react';
import { api } from '../../../shared/api/api';
import type { Disease } from '../../../shared/types/index';
import type { Doc, DocForm } from '../../../shared/types/documents';

const blank: DocForm = {
  disease_id: '',
  title: '',
  publisher: '',
  source_url: '',
  usage_note: 'Tóm tắt có nguồn; chưa được chuyên gia y tế thẩm định.',
  content: '',
  published: false,
  expected_version: null,
};
export function DocumentManager({
  diseases,
  toast,
}: {
  diseases: Disease[];
  toast: (s: string) => void;
}) {
  const [docs, setDocs] = useState<Doc[]>([]),
    [editing, setEditing] = useState<string | null>(null),
    [form, setForm] = useState<DocForm>(blank),
    [busy, setBusy] = useState(false),
    [error, setError] = useState('');
  const [versions, setVersions] = useState<
    { version: number; title: string; content: string; checksum: string }[]
  >([]);
  const [historyId, setHistoryId] = useState('');
  const load = async () => {
    try {
      setDocs(await api<Doc[]>('/admin/documents'));
    } catch (e) {
      setError((e as Error).message);
    }
  };
  useEffect(() => {
    void load();
  }, []);
  const edit = (doc?: Doc) => {
    setError('');
    setHistoryId('');
    setEditing(doc?.id || 'new');
    setForm(
      doc
        ? {
            disease_id: doc.disease_id,
            title: doc.title,
            publisher: doc.publisher,
            source_url: doc.source_url,
            usage_note: doc.usage_note,
            content: doc.content,
            published: doc.published,
            expected_version: doc.version,
          }
        : { ...blank, disease_id: diseases[0]?.id || '' },
    );
  };
  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await api('/admin/documents' + (editing === 'new' ? '' : '/' + editing), {
        method: editing === 'new' ? 'POST' : 'PUT',
        body: JSON.stringify(form),
      });
      setEditing(null);
      await load();
      toast('Đã lưu tài liệu với phiên bản mới.');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const showVersions = async (id: string) => {
    try {
      setVersions(await api('/admin/documents/' + id + '/versions'));
      setHistoryId(id);
      setEditing(null);
    } catch (e) {
      setError((e as Error).message);
    }
  };
  const text = (
    key: 'title' | 'publisher' | 'source_url' | 'usage_note',
    label: string,
    maxLength: number,
  ) => (
    <label>
      {label}
      <input
        required
        type={key === 'source_url' ? 'url' : 'text'}
        maxLength={maxLength}
        value={form[key]}
        onChange={(e) => setForm({ ...form, [key]: e.target.value })}
      />
    </label>
  );
  return (
    <section className="document-manager">
      <div className="results-heading">
        <h2>Kho tài liệu tham khảo</h2>
        <button className="button secondary" onClick={() => edit()} disabled={busy}>
          <Plus size={16} />
          Thêm tài liệu
        </button>
      </div>
      <p className="muted">
        Tài liệu đã xuất bản của chủ đề đang hiển thị mới được dùng để trả lời câu hỏi. Mỗi lần lưu
        giữ một phiên bản nội dung.
      </p>
      {error && (
        <p className="error-text" role="alert">
          {error}
        </p>
      )}
      {editing ? (
        <div className="panel">
          <div className="section-title">
            <h2>{editing === 'new' ? 'Tài liệu mới' : 'Biên tập tài liệu'}</h2>
            <button
              className="icon-button"
              disabled={busy}
              onClick={() => setEditing(null)}
              aria-label="Đóng biên tập tài liệu"
            >
              <X size={18} />
            </button>
          </div>
          <form className="auth-form" onSubmit={save}>
            <label>
              Chủ đề liên kết
              <select
                value={form.disease_id}
                onChange={(e) => setForm({ ...form, disease_id: e.target.value })}
                required
              >
                {diseases.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </label>
            {text('title', 'Tên tài liệu', 200)}
            {text('publisher', 'Đơn vị xuất bản', 150)}
            {text('source_url', 'URL nguồn (HTTPS)', 1000)}
            {text('usage_note', 'Điều kiện sử dụng / ghi chú biên tập', 1000)}
            <label>
              Nội dung đã kiểm tra quyền sử dụng
              <textarea
                required
                minLength={20}
                maxLength={12000}
                value={form.content}
                onChange={(e) => setForm({ ...form, content: e.target.value })}
              />
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={form.published}
                onChange={(e) => setForm({ ...form, published: e.target.checked })}
              />
              Xuất bản tài liệu vào kho tra cứu
            </label>
            <p className="muted">
              Chỉ nhập nội dung có quyền sử dụng và kiểm tra nguồn trước khi xuất bản. Không dùng
              thông tin sức khỏe cá nhân làm tài liệu.
            </p>
            <div className="modal-actions">
              <button
                className="button secondary"
                type="button"
                disabled={busy}
                onClick={() => setEditing(null)}
              >
                Hủy
              </button>
              <button className="button primary" disabled={busy}>
                {busy ? 'Đang lưu…' : 'Lưu phiên bản'}
                <Check size={16} />
              </button>
            </div>
          </form>
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Tài liệu</th>
                <th>Trạng thái</th>
                <th>Phiên bản</th>
                <th>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id}>
                  <td>
                    <strong>{d.title}</strong>
                    <small>{d.publisher}</small>
                  </td>
                  <td>
                    <span className={'state-badge ' + (!d.published ? 'draft' : '')}>
                      {d.published ? 'Đã xuất bản' : 'Bản nháp'}
                    </span>
                  </td>
                  <td>v{d.version}</td>
                  <td>
                    <div className="document-actions">
                      <button className="text-button" onClick={() => edit(d)}>
                        Sửa
                      </button>
                      <button className="text-button" onClick={() => showVersions(d.id)}>
                        Phiên bản
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {historyId && (
        <div className="panel document-versions">
          <div className="section-title">
            <h2>Lịch sử nội dung</h2>
            <button
              className="icon-button"
              onClick={() => setHistoryId('')}
              aria-label="Đóng lịch sử nội dung"
            >
              <X size={18} />
            </button>
          </div>
          {versions.map((v) => (
            <details key={v.version}>
              <summary>
                v{v.version} · {v.title}
                <ChevronDown size={15} />
              </summary>
              <p className="passage-content">{v.content}</p>
              <small className="checksum">SHA256: {v.checksum}</small>
            </details>
          ))}
        </div>
      )}
    </section>
  );
}
