import { useEffect, useState } from 'react';
import { Bookmark, Check } from 'lucide-react';
import { api } from '../../../shared/api/api';
import type { Disease, User } from '../../../shared/types/index';

export function SaveButton({
  user,
  auth,
  toast,
  mode,
  query,
  items,
}: {
  user: User | null;
  auth: () => void;
  toast: (s: string) => void;
  mode: 'keyword' | 'symptom' | 'image';
  query: string;
  items: Pick<Disease, 'id'>[];
}) {
  const [busy, setBusy] = useState(false),
    [saved, setSaved] = useState(false);
  const resultKey = items.map((item) => item.id).join(',');
  useEffect(() => setSaved(false), [query, resultKey, mode, user?.id]);
  const save = async () => {
    if (!user) {
      auth();
      return;
    }
    setBusy(true);
    try {
      await api('/history', {
        method: 'POST',
        body: JSON.stringify({ consent: true, mode, query: query.slice(0, 300), result_ids: Array.from(new Set(items.map((d) => d.id))).slice(0, 30) }),
      });
      setSaved(true);
      toast('Đã lưu vào lịch sử của bạn. Bạn có thể xóa bất cứ lúc nào.');
    } catch (e) {
      toast((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="save-choice">
      <button className="button secondary small" onClick={save} disabled={busy || saved}>
        {saved ? <Check size={16} /> : <Bookmark size={16} />}{' '}
        {saved ? 'Đã lưu' : busy ? 'Đang lưu…' : 'Đồng ý lưu tra cứu'}
      </button>
      <small>Chỉ lưu khi bạn bấm nút này.</small>
    </div>
  );
}
