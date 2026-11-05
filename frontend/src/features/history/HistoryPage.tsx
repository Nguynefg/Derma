import { useEffect, useState } from 'react';
import {
  ArrowRight,
  ArrowUpRight,
  Bookmark,
  LoaderCircle,
  LockKeyhole,
  Search,
  Stethoscope,
  Trash2,
} from 'lucide-react';
import { api } from '../../shared/api/api';
import type { User, HistoryItem } from '../../shared/types/index';
import { formatDate } from '../../shared/utils/date';
import { Modal } from '../../shared/components/Modal';
import { Heading } from '../../shared/components/Heading';

export function HistoryPage({
  user,
  auth,
  open,
  toast,
}: {
  user: User | null;
  auth: () => void;
  open: (id: string) => void;
  toast: (s: string) => void;
}) {
  const [items, setItems] = useState<HistoryItem[]>([]),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(''),
    [confirm, setConfirm] = useState(false);
  const load = async () => {
    setBusy(true);
    try {
      setItems(await api<HistoryItem[]>('/history'));
      setError('');
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => {
    if (user) void load();
    else setItems([]);
  }, [user]);
  const remove = async (id?: string) => {
    try {
      await api('/history' + (id ? '/' + id : ''), { method: 'DELETE' });
      setConfirm(false);
      await load();
      toast('Đã xóa lịch sử đã chọn.');
    } catch (e) {
      toast((e as Error).message);
    }
  };
  return (
    <>
      <Heading
        eyebrow="KHÔNG GIAN CỦA BẠN"
        title="Những điều bạn đã lưu."
        description="Chỉ những lượt tra cứu bạn đồng ý lưu mới xuất hiện ở đây."
      />
      {!user ? (
        <div className="empty">
          <LockKeyhole size={34} />
          <h2>Lịch sử dành riêng cho bạn</h2>
          <p>Đăng nhập để xem hoặc xóa các lượt tra cứu đã lưu.</p>
          <button className="button primary" onClick={auth}>
            Đăng nhập <ArrowRight size={16} />
          </button>
        </div>
      ) : error ? (
        <div className="inline-note error">
          {error}
          <button onClick={load}>Thử lại</button>
        </div>
      ) : busy ? (
        <div className="loading-state">
          <LoaderCircle className="spin" />
        </div>
      ) : !items.length ? (
        <div className="empty">
          <Bookmark size={34} />
          <h2>Chưa có lượt tra cứu nào</h2>
          <p>Khi muốn giữ lại kết quả, hãy chọn “Đồng ý lưu tra cứu”.</p>
        </div>
      ) : (
        <>
          <div className="results-heading">
            <p>{items.length} lượt tra cứu gần nhất</p>
            <button className="text-button danger" onClick={() => setConfirm(true)}>
              <Trash2 size={16} />
              Xóa tất cả
            </button>
          </div>
          <div className="history-list">
            {items.map((h) => (
              <article className="history-item" key={h.id}>
                <span className="quick-icon mint">
                  {h.mode === 'keyword' ? <Search size={20} /> : <Stethoscope size={20} />}
                </span>
                <div>
                  <small>
                    {h.mode === 'keyword' ? 'Từ khóa' : 'Triệu chứng'} · {formatDate(h.created_at)}
                  </small>
                  <h3>{h.query || 'Toàn bộ thư viện'}</h3>
                  <div className="history-links">
                    {h.results.map((r) => (
                      <button key={r.id} onClick={() => open(r.id)}>
                        {r.name}
                        <ArrowUpRight size={12} />
                      </button>
                    ))}
                  </div>
                </div>
                <button
                  className="icon-button danger"
                  aria-label={'Xóa tra cứu ' + h.query}
                  onClick={() => remove(h.id)}
                >
                  <Trash2 size={18} />
                </button>
              </article>
            ))}
          </div>
        </>
      )}
      {confirm && (
        <Modal title="Xóa toàn bộ lịch sử?" onClose={() => setConfirm(false)}>
          <p>Các lượt tra cứu đã lưu sẽ bị xóa khỏi tài khoản. Hành động này không thể hoàn tác.</p>
          <div className="modal-actions">
            <button className="button secondary" onClick={() => setConfirm(false)}>
              Giữ lại
            </button>
            <button className="button danger-fill" onClick={() => remove()}>
              Xóa lịch sử
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}
