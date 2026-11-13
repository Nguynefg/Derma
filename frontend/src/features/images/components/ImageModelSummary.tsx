import { useEffect, useState } from 'react';
import { ScanLine } from 'lucide-react';
import { api } from '../../../shared/api/api';
import type { ModelState } from '../../../shared/types/images';

export function ImageModelSummary() {
  const [state, setState] = useState<ModelState | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 8000);
    api<{ image_model: ModelState; message?: string }>('/models/status', {
      signal: controller.signal,
    })
      .then((r) =>
        setState({
          ...r.image_model,
          message: r.image_model.message || r.message || 'Chưa có mô hình nhận diện đã cấu hình.',
        }),
      )
      .catch(() => {})
      .finally(() => clearTimeout(timer));
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, []);
  return (
    <>
      <h3>
        <ScanLine size={18} />
        Trạng thái phần ảnh
      </h3>
      <p>
        <span className="state-badge">Kiểm tra chất lượng đã có</span>
      </p>
      <p>
        <span className={'state-badge ' + (state?.status === 'ready' ? '' : 'draft')}>
          {state?.status === 'ready' ? 'Mô hình nghiên cứu đã cấu hình' : 'Nhận diện chưa sẵn sàng'}
        </span>
      </p>
      <p className="muted">{state?.message || 'Chưa đọc được trạng thái mô hình từ máy chủ.'}</p>
      {state?.version && (
        <p className="muted">
          Phiên bản {state.version} · {state.label_count || 0} nhóm
        </p>
      )}
      {!!state?.data_limitations?.length && (
        <details className="model-limitations">
          <summary>Giới hạn của mô hình</summary>
          <ul>
            {state.data_limitations.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </details>
      )}
    </>
  );
}
