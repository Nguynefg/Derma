import { Modal } from '../../../shared/components/Modal';
import { Trash2, LoaderCircle } from 'lucide-react';
import { useEffect, useState } from 'react';
import { api } from '../../../shared/api/api';
import type { Disease } from '../../../shared/types/index';

type Record = {
  id: string;
  image_url: string;
  image_type: string;
  is_reference: boolean;
  disease_id: string | null;
  disease_name: string | null;
};

export function ImageArchive({
  admin = false,
  diseases = [],
  refreshKey = '',
  userId = '',
}: {
  admin?: boolean;
  diseases?: Disease[];
  refreshKey?: string;
  userId?: string;
}) {
  const [statusFilter, setStatusFilter] = useState('');
  const [query, setQuery] = useState('');
  const [preview, setPreview] = useState<Record | null>(null);
  const [pendingDelete, setPendingDelete] = useState<Record | null>(null);
  const [deleteError, setDeleteError] = useState('');
  const [drafts, setDrafts] = useState<{ [key: string]: string }>({});
  const [items, setItems] = useState<Record[]>([]),
    [error, setError] = useState(''),
    [busy, setBusy] = useState('');
  const visible = items.filter(
    (r) =>
      (!statusFilter || r.is_reference === (statusFilter === 'approved')) &&
      `${r.disease_name || ''} ${r.id}`.toLowerCase().includes(query.toLowerCase()),
  );
  const load = async () => {
    try {
      setItems(await api<Record[]>(admin ? '/admin/image-records' : '/images/records'));
      setError('');
    } catch (e) {
      setError((e as Error).message);
    }
  };
  useEffect(() => {
    void load();
  }, [admin, refreshKey, userId]);
  const label = async (record: Record, diseaseId: string) => {
    setBusy(record.id);
    setError('');
    try {
      await api('/admin/image-records/' + record.id, {
        method: 'PUT',
        body: JSON.stringify({ disease_id: diseaseId || null, is_reference: Boolean(diseaseId) }),
      });
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy('');
    }
  };
  const remove = async (record: Record) => {
    if (busy) return;
    setBusy(record.id);
    setDeleteError('');
    try {
      await api('/images/records/' + record.id, { method: 'DELETE' });
      setItems((current) => current.filter((item) => item.id !== record.id));
      setPendingDelete(null);
      if (preview?.id === record.id) setPreview(null);
      await load();
    } catch (e) {
      setDeleteError((e as Error).message);
    } finally {
      setBusy('');
    }
  };
  return (
    <section className="panel image-archive">
      <h2>{admin ? 'Kho ảnh mẫu và ảnh chờ gắn nhãn' : 'Ảnh bạn đã lưu'}</h2>
      <p className="muted">
        {admin
          ? '100 ảnh tải lên gần nhất. Chỉ gắn nhãn sau khi kiểm tra nguồn ảnh và bệnh lý; nhãn quản trị không tương đương chẩn đoán y khoa.'
          : 'Ảnh chưa được gắn nhãn sẽ không tự trở thành ảnh mẫu. Bạn có thể xóa ảnh đã lưu.'}
      </p>
      {admin && (
        <div className="management-toolbar">
          <input
            aria-label="Tìm ảnh trong kho"
            placeholder="Tên bệnh đã gắn hoặc mã ảnh…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <select
            aria-label="Trạng thái duyệt ảnh"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">Tất cả ảnh</option>
            <option value="pending">Chờ duyệt</option>
            <option value="approved">Đã gắn nhãn</option>
          </select>
          <span className="muted">{visible.length} ảnh</span>
        </div>
      )}
      {error && (
        <p className="error-text" role="alert">
          {error}
        </p>
      )}
      {!visible.length ? (
        <p className="muted">Chưa có ảnh đã lưu.</p>
      ) : (
        <div className="image-archive-grid">
          {visible.map((record) => (
            <article key={record.id}>
              <button
                className="image-preview-button"
                aria-label={'Xem ảnh ' + record.id}
                onClick={() => setPreview(record)}
              >
                <img src={record.image_url} alt="Ảnh đã lưu để đối chiếu" loading="lazy" />
              </button>
              <span className={'state-badge ' + (record.is_reference ? '' : 'draft')}>
                {record.is_reference ? record.disease_name : 'Chưa rõ · Chờ gắn nhãn'}
              </span>
              <small>{record.image_type === 'clinical' ? 'Ảnh thông thường' : 'Ảnh soi da'}</small>
              {admin && (
                <label>
                  Gắn với bệnh lý
                  <select
                    aria-label="Bệnh lý của ảnh mẫu"
                    disabled={busy === record.id}
                    value={drafts[record.id] ?? record.disease_id ?? ''}
                    onChange={(e) => setDrafts({ ...drafts, [record.id]: e.target.value })}
                  >
                    <option value="">Chưa rõ / Bỏ nhãn ảnh mẫu</option>
                    {diseases
                      .filter((d) => d.photo_supported)
                      .filter((d) => d.published)
                      .map((d) => (
                        <option value={d.id} key={d.id}>
                          {d.name}
                        </option>
                      ))}
                  </select>
                </label>
              )}
              {admin && (
                <button
                  className="button secondary"
                  disabled={busy === record.id}
                  onClick={() => void label(record, drafts[record.id] ?? record.disease_id ?? '')}
                >
                  {busy === record.id
                    ? 'Đang duyệt…'
                    : (drafts[record.id] ?? record.disease_id)
                      ? 'Duyệt & gắn nhãn'
                      : 'Xác nhận chưa rõ'}
                </button>
              )}
              <button
                className="text-button danger"
                disabled={busy === record.id}
                onClick={() => {
                  setDeleteError('');
                  setPendingDelete(record);
                }}
              >
                Xóa ảnh
              </button>
            </article>
          ))}
        </div>
      )}
      {preview && (
        <Modal title="Kiểm tra ảnh trước khi duyệt" wide onClose={() => setPreview(null)}>
          <img className="review-image" src={preview.image_url} alt="Ảnh cần kiểm tra" />
          <p className="muted">
            Mã ảnh {preview.id} · {preview.disease_name || 'Chưa được gắn nhãn'}
          </p>
        </Modal>
      )}
      {pendingDelete && (
        <Modal
          title="Xác nhận xóa ảnh"
          onClose={() => {
            if (!busy) setPendingDelete(null);
          }}
        >
          <div className="delete-image-confirm">
            <span className="delete-confirm-icon">
              <Trash2 size={26} />
            </span>
            <h3>Bạn muốn xóa ảnh này?</h3>
            <img src={pendingDelete.image_url} alt="Ảnh đang chờ xác nhận xóa" />
            <p className="muted">
              Ảnh sẽ được xóa khỏi kho và không thể khôi phục.
              {pendingDelete.is_reference &&
                ' Ảnh mẫu này cũng sẽ không còn được dùng để đối chiếu.'}
            </p>
            {deleteError && (
              <p className="error-text" role="alert">
                {deleteError}
              </p>
            )}
            <div className="delete-confirm-actions">
              <button
                className="button secondary"
                type="button"
                disabled={Boolean(busy)}
                onClick={() => setPendingDelete(null)}
              >
                Hủy
              </button>
              <button
                className="button delete-confirm-button"
                type="button"
                disabled={Boolean(busy)}
                onClick={() => void remove(pendingDelete)}
              >
                {busy ? <LoaderCircle size={17} className="spin" /> : <Trash2 size={17} />}
                {busy ? 'Đang xóa…' : 'Xóa ảnh'}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </section>
  );
}
