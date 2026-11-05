import { useEffect, useState } from 'react';
import { BookOpen, ExternalLink, Info, LoaderCircle, ShieldCheck } from 'lucide-react';
import { api } from '../../../shared/api/api';
import { Modal } from '../../../shared/components/Modal';
import { SkinIllustration } from './SkinIllustration';
import { hasLibraryContent, libraryScope } from '../../../shared/utils/libraryPresentation';

const specialties: Record<string, string> = {
  '05': 'Nội tiết',
  '08': 'Thần kinh',
  '10': 'Tai mũi họng',
  '11': 'Tim mạch',
  '12': 'Hô hấp',
  '13': 'Tiêu hóa',
  '14': 'Da liễu',
  '15': 'Cơ xương khớp',
  '16': 'Thận & tiết niệu',
};
type Detail = {
  id: string;
  title: string;
  original_title?: string;
  chapter_title?: string;
  group_name?: string;
  code: string | null;
  kind_name: string;
  chapter: string;
  uri: string;
  source_url: string;
  chapters: { id: string; title: string; content: string }[];
  article_content?: { summary: string; details: string; risk_factors: string; prevention: string };
  editorial_source?: { title: string; url: string };
};
export function ICDDetailModal({ id, onClose }: { id: string; onClose: () => void }) {
  const [detail, setDetail] = useState<Detail | null>(null),
    [error, setError] = useState('');
  useEffect(() => {
    const c = new AbortController();
    setDetail(null);
    setError('');
    api<Detail>('/icd/' + id, { signal: c.signal })
      .then((r) => {
        if (!c.signal.aborted) setDetail(r);
      })
      .catch((e) => {
        if (!c.signal.aborted) setError(e.message);
      });
    return () => c.abort();
  }, [id]);
  const groupName = detail
    ? detail.group_name ||
      (detail.chapter === 'X' ? 'Thông tin bổ sung' : detail.chapter_title || 'Chưa phân nhóm')
    : '';
  const scope = libraryScope(detail?.chapter, groupName);
  return (
    <Modal title="Thông tin thư viện" onClose={onClose} wide>
      {error ? (
        <p role="alert" className="error-text">
          {error}
        </p>
      ) : !detail ? (
        <div className="loading-state">
          <LoaderCircle className="spin" />
          Đang mở…
        </div>
      ) : (
        <>
          <div className="detail-kicker">
            Thư viện sức khỏe <span>•</span> {groupName}
          </div>
          <h1 className="detail-title">{detail.title}</h1>
          {detail.original_title && detail.original_title !== detail.title && (
            <p className="muted">{detail.original_title}</p>
          )}
          <div className="icd-detail-actions">
            <a
              className="button secondary"
              href={detail.source_url}
              target="_blank"
              rel="noreferrer"
            >
              <BookOpen size={16} /> Đọc nguồn WHO <ExternalLink size={16} />
            </a>
          </div>
          <SkinIllustration
            disease={{
              name: detail.title,
              category: 'Kiến thức sức khỏe',
              specialty: specialties[detail.chapter] || 'Kiến thức sức khỏe',
            }}
          />
          <p className="detail-summary">
            {hasLibraryContent(detail.article_content?.summary) ? detail.article_content?.summary : scope.text}
          </p>
          <div className="inline-note">
            <Info size={18} aria-hidden="true" />
            Thông tin hỗ trợ tìm hiểu sức khỏe, không thay thế chẩn đoán của bác sĩ.
          </div>
          {hasLibraryContent(detail.article_content?.details) && <section className="detail-section">
            <h3>Tổng quan</h3>
            <p>
              {detail.article_content?.details ||
                `Nội dung này thuộc nhóm ${groupName}. Bạn có thể đối chiếu tên tiếng Anh và đọc tài liệu nguồn để tìm hiểu thêm.`}
            </p>
            <dl className="icd-detail-facts">
              <div>
                <dt>Nhóm chủ đề</dt>
                <dd>{groupName}</dd>
              </div>
              <div>
                <dt>Ngôn ngữ nguồn</dt>
                <dd>Tiếng Anh</dd>
              </div>
            </dl>
          </section>}
          {!hasLibraryContent(detail.article_content?.details) && <p className="muted">Nhóm chủ đề: {groupName}</p>}
          {detail.article_content && (
            <>
              {hasLibraryContent(detail.article_content.risk_factors) && <section className="detail-section">
                <h3>Yếu tố liên quan</h3>
                <p>{detail.article_content.risk_factors}</p>
              </section>}
              {hasLibraryContent(detail.article_content.prevention) && <section className="detail-section">
                <h3>Phòng ngừa & chăm sóc</h3>
                <p>{detail.article_content.prevention}</p>
              </section>}
            </>
          )}
          <section className="detail-section sources-box">
            <h3>
              <ShieldCheck size={19} /> Nguồn tham khảo
            </h3>
            <a href={detail.source_url} target="_blank" rel="noreferrer">
              <div>
                <strong>{detail.title}</strong>
                <small>World Health Organization · Tài liệu nguồn</small>
              </div>
              <ExternalLink size={18} />
            </a>
            {detail.editorial_source && (
              <a href={detail.editorial_source.url} target="_blank" rel="noreferrer">
                <div>
                  <strong>{detail.editorial_source.title}</strong>
                  <small>Nguồn bài biên soạn</small>
                </div>
                <ExternalLink size={18} />
              </a>
            )}
          </section>
        </>
      )}
    </Modal>
  );
}
