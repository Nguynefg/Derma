import { useEffect, useState } from 'react';
import { ExternalLink, FileText } from 'lucide-react';
import { api } from '../../../shared/api/api';
import type { Doc } from '../../../shared/types/documents';

export function DocumentSources() {
  const [docs, setDocs] = useState<Doc[]>([]),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(true);
  useEffect(() => {
    api<Doc[]>('/documents')
      .then(setDocs)
      .catch((e) => setError(e.message))
      .finally(() => setBusy(false));
  }, []);
  return (
    <div className="source-list">
      {busy ? (
        <p className="muted">Đang tải tài liệu…</p>
      ) : error ? (
        <p className="error-text">{error}</p>
      ) : docs.length ? (
        docs.map((d) => (
          <a key={d.id} className="source-row" href={d.source_url} target="_blank" rel="noreferrer">
            <span className="source-number">
              <FileText size={20} />
            </span>
            <span>
              <strong>{d.title}</strong>
              <small>
                {d.publisher} · Nội dung v{d.version}
              </small>
              <p>{d.usage_note}</p>
            </span>
            <ExternalLink size={19} />
          </a>
        ))
      ) : (
        <p className="muted">Chưa có tài liệu đang xuất bản.</p>
      )}
    </div>
  );
}
