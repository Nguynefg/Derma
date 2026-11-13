import { Reply, type ImageChatContext } from '../assistant/components/AssistantChat';
import { useEffect, useRef, useState } from 'react';
import {
  ArrowRight,
  Camera,
  Check,
  Crop,
  FileImage,
  Focus,
  Info,
  Lightbulb,
  LoaderCircle,
  LockKeyhole,
  ShieldCheck,
  Sun,
  UploadCloud,
  X,
} from 'lucide-react';
import { api } from '../../shared/api/api';
import { PageHeading } from '../../shared/components/Decor';
import type { User } from '../../shared/types/index';
import { ImageArchive } from './components/ImageArchive';
import { SaveButton } from '../profile/components/SaveButton';
import { WebSources, type WebSource } from '../../shared/components/WebSources';

type Quality = {
  status: 'needs_review' | 'no_obvious_issue';
  lighting: 'low' | 'high' | 'balanced';
  detail: 'limited' | 'visible';
  metrics: { brightness: number; contrast: number; detail_variance: number };
  issues: { code: string; message: string }[];
  notice: string;
};
type Result = {
  status: string;
  reason?: string;
  message: string;
  observations?: string;
  observation_labels?: { id: string; name: string }[];
  width: number;
  height: number;
  original_width: number;
  original_height: number;
  crop: { x: number; y: number; width: number; height: number } | null;
  quality: Quality;
  model_version?: string;
  score_notice?: string;
  usage_note?: string;
  method?: string;
  group?: { label: string; name: string; score: number };
  related_articles?: { disease_id: string; name: string }[];
  stored: boolean;
  image_record_id?: string | null;
  database_match?: { status: 'matched' | 'missing_article' | 'inconclusive' | 'not_evaluated'; message: string };
  external_sources?: WebSource[];
  search_suggestions_html?: string;
  fallback?: { status: string; reason?: string; message?: string; model?: string; upstream_status?: number; error_kind?: string };
  external_result?: { status: string; reply: string; evidence_status?: string; source_reply?: string; source_lookup?: {status: string; message?: string}; external_sources?: WebSource[]; search_suggestions_html?: string };
  candidates?: {
    disease_id: string;
    name: string;
    score: number;
    english_name: string;
    category: string;
    summary: string;
    content_version: number;
    photo_scope?: { code: string; name: string; note: string };
  }[];
};

type Region = { x: number; y: number; width: number; height: number };
const defaultRegion: Region = { x: 10, y: 10, width: 80, height: 80 };

export function ImagePage({
  discuss,
  symptoms,
  open,
  user,
  auth,
}: {
  discuss: (context: ImageChatContext) => void;
  symptoms: () => void;
  open: (id: string) => void;
  user: User | null;
  auth: () => void;
}) {
  const [file, setFile] = useState<File | null>(null),
    [preview, setPreview] = useState(''),
    [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [cropEnabled, setCropEnabled] = useState(false),
    [region, setRegion] = useState<Region>(defaultRegion);
  const [busy, setBusy] = useState(false),
    [drag, setDrag] = useState(false),
    [error, setError] = useState(''),
    [result, setResult] = useState<Result | null>(null);
  const [saveImage, setSaveImage] = useState(false);
  const input = useRef<HTMLInputElement>(null),
    request = useRef<AbortController | null>(null),
    mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      request.current?.abort();
    };
  }, []);
  useEffect(() => {
    if (!file) {
      setPreview('');
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  const choose = (next?: File) => {
    if (busy) return;
    setResult(null);
    setError('');
    setFile(null);
    setDimensions({ width: 0, height: 0 });
    setCropEnabled(false);
    setRegion(defaultRegion);
    if (input.current) input.current.value = '';
    if (!next) return;
    if (next.size > 5 * 1024 * 1024) {
      setError('Ảnh phải nhỏ hơn hoặc bằng 5 MB.');
      return;
    }
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(next.type)) {
      setError('Vui lòng chọn ảnh JPEG, PNG hoặc WebP.');
      return;
    }
    setFile(next);
  };
  const updateRegion = (key: keyof Region, value: number) => {
    const next = { ...region, [key]: value };
    if (key === 'x') next.width = Math.min(next.width, 100 - value);
    if (key === 'y') next.height = Math.min(next.height, 100 - value);
    setRegion(next);
    setResult(null);
    setError('');
  };
  const selectedWidth = cropEnabled
    ? Math.round((dimensions.width * region.width) / 100)
    : dimensions.width;
  const selectedHeight = cropEnabled
    ? Math.round((dimensions.height * region.height) / 100)
    : dimensions.height;
  const tooSmall = Boolean(dimensions.width) && (selectedWidth < 224 || selectedHeight < 224);
  const tooLarge = dimensions.width * dimensions.height > 12_000_000;
  const analyze = async () => {
    if (saveImage && !user) {
      auth();
      return;
    }
    if (!file || busy || tooSmall || tooLarge) return;
    setBusy(true);
    setError('');
    setResult(null);
    const controller = new AbortController();
    request.current = controller;
    const timer = setTimeout(() => controller.abort('timeout'), 90000);
    const data = new FormData();
    data.append('file', file);
    data.append('image_type', 'clinical');
    data.append('save_image', String(saveImage));
    data.append('analysis_mode', 'ai');
    data.append('allow_external_ai', 'true');
    data.append('observations', JSON.stringify({ site: 'unspecified', label_ids: [] }));
    if (cropEnabled)
      data.append(
        'crop',
        JSON.stringify(
          Object.fromEntries(Object.entries(region).map(([key, value]) => [key, value / 100])),
        ),
      );
    try {
      const value = await api<Result>('/images/analyze', {
        method: 'POST',
        body: data,
        signal: controller.signal,
      });
      if (mounted.current) {
        setResult(value);
      }
    } catch (e) {
      if (mounted.current) {
        const message = (e as Error).message;
        setError(
          controller.signal.reason === 'timeout'
            ? 'Kiểm tra mất quá nhiều thời gian. Vui lòng thử lại.'
            : controller.signal.aborted
              ? 'Đã hủy yêu cầu kiểm tra.'
              : message === 'Not Found'
                ? 'Máy chủ đang dùng API cũ. Hãy khởi động lại web để dùng chức năng mới.'
                : message,
        );
      }
    } finally {
      clearTimeout(timer);
      if (mounted.current) setBusy(false);
    }
  };
  const [saveNotice, setSaveNotice] = useState('');
  useEffect(() => setSaveNotice(''), [result]);
  const hasFindings = Boolean(result && (result.group || result.observations || result.candidates?.length));
  const hasSupplement = Boolean(result?.external_result?.reply?.trim());
  const resultHeading = result?.reason === 'model_unavailable'
    ? 'Mô hình phân tích hiện chưa sẵn sàng'
    : ({
        insufficient_confidence: 'Chưa đủ độ tin cậy để gợi ý nhóm bệnh',
        quality_review_required: 'Cần ảnh rõ hơn để tiếp tục',
        out_of_scope: 'Ảnh nằm ngoài phạm vi hỗ trợ',
        catalog_mismatch: 'Thư viện chưa có bài phù hợp với nhãn gợi ý',
      } as Record<string, string>)[result?.status || ''] || 'Chưa có kết quả đủ cơ sở';
  return (
    <>
      <PageHeading
        variant="images"
        eyebrow="PHÂN TÍCH ẢNH · BẢN NGHIÊN CỨU"
        title="Hiểu thêm từ hình ảnh."
        description="Phân tích ảnh bằng AI và tham khảo bệnh lý trong thư viện."
      />
      <div className="image-flow" aria-label="Các bước kiểm tra ảnh">
        <span className={file ? 'done' : 'active'}>
          <i>{file ? <Check size={15} /> : 1}</i>Chọn ảnh
        </span>
        <span className={file && !result ? 'active' : ''}>
          <i>2</i>Kiểm tra vùng ảnh
        </span>
        <span className={result ? 'active' : ''}>
          <i>3</i>Đọc kết quả
        </span>
      </div>
      <div className="image-workspace">
        <section className="panel image-editor">
          <div className="image-section-title">
            <h2>
              <Camera size={21} />
              Ảnh của bạn
            </h2>
            <span className="image-private">
              <LockKeyhole size={13} />
              {saveImage ? 'Lưu ảnh riêng tư' : 'Không lưu ảnh'}
            </span>
          </div>
          <input
            ref={input}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            aria-label="Chọn ảnh"
            className="visually-hidden"
            onChange={(e) => choose(e.target.files?.[0])}
          />
          {!file ? (
            <button
              className={'dropzone image-upload-studio ' + (drag ? 'drag' : '')}
              onClick={() => input.current?.click()}
              onDragOver={(e) => {
                e.preventDefault();
                setDrag(true);
              }}
              onDragLeave={() => setDrag(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDrag(false);
                choose(e.dataTransfer.files[0]);
              }}
            >
              <span className="upload-icon">
                <UploadCloud size={36} />
              </span>
              <h3>Thả ảnh vào đây</h3>
              <p>
                hoặc <span>chọn từ thiết bị</span>
              </p>
              <small>JPEG, PNG, WebP · Tối đa 5 MB · Mỗi chiều từ 224 px</small>
            </button>
          ) : (
            <>
              <div
                className={
                  'image-preview-stage image-preview-motion ' + (busy ? 'is-analyzing' : '')
                }
                aria-busy={busy}
              >
                <div
                  className="image-preview-frame"
                  style={
                    dimensions.width
                      ? {
                          aspectRatio: dimensions.width / dimensions.height,
                          maxWidth: (390 * dimensions.width) / dimensions.height,
                        }
                      : undefined
                  }
                >
                  <img
                    src={preview}
                    alt="Ảnh đã chọn để kiểm tra"
                    onLoad={(e) =>
                      setDimensions({
                        width: e.currentTarget.naturalWidth,
                        height: e.currentTarget.naturalHeight,
                      })
                    }
                    onError={() => {
                      setError('Không thể đọc ảnh đã chọn. Vui lòng dùng tệp khác.');
                      setFile(null);
                    }}
                  />
                  {busy && (
                    <div className="image-scan-overlay" role="status">
                      <span className="image-scan-line" />
                      <div>
                        <Focus size={18} />
                        <span>
                          Đang phân tích ảnh
                          <span className="analysis-dots" aria-hidden="true">
                            …
                          </span>
                        </span>
                      </div>
                    </div>
                  )}
                  {cropEnabled && (
                    <div
                      className="crop-selection"
                      aria-hidden="true"
                      style={{
                        left: region.x + '%',
                        top: region.y + '%',
                        width: region.width + '%',
                        height: region.height + '%',
                      }}
                    >
                      <span>Vùng kiểm tra</span>
                      <i />
                      <i />
                      <i />
                      <i />
                    </div>
                  )}
                </div>
              </div>
              <div className="file-info">
                <FileImage size={20} />
                <span>
                  <strong>{file.name}</strong>
                  <small>
                    {(file.size / 1024).toFixed(0)} KB · {dimensions.width} × {dimensions.height} px
                  </small>
                </span>
                <button
                  disabled={busy}
                  className="icon-button"
                  aria-label="Bỏ ảnh"
                  onClick={() => choose()}
                >
                  <X size={18} />
                </button>
              </div>
              <div className="crop-toggle">
                <label>
                  <input
                    type="checkbox"
                    checked={cropEnabled}
                    disabled={busy}
                    onChange={(e) => {
                      setCropEnabled(e.target.checked);
                      setResult(null);
                    }}
                  />
                  <Crop size={17} />
                  Chọn vùng cần kiểm tra
                </label>
                <button
                  className="text-button"
                  disabled={busy}
                  onClick={() => input.current?.click()}
                >
                  Đổi ảnh
                </button>
              </div>
              {cropEnabled && (
                <div className="crop-controls">
                  <p>Điều chỉnh khung để giữ vùng bạn quan tâm và một ít da xung quanh.</p>
                  <div>
                    {(
                      [
                        ['x', 'Vị trí ngang'],
                        ['y', 'Vị trí dọc'],
                        ['width', 'Chiều rộng'],
                        ['height', 'Chiều cao'],
                      ] as const
                    ).map(([key, label]) => (
                      <label key={key}>
                        <span>
                          {label}
                          <strong>{region[key]}%</strong>
                        </span>
                        <input
                          type="range"
                          aria-label={label}
                          min={key === 'width' || key === 'height' ? 5 : 0}
                          max={
                            key === 'width'
                              ? 100 - region.x
                              : key === 'height'
                                ? 100 - region.y
                                : 95
                          }
                          value={region[key]}
                          disabled={busy}
                          onChange={(e) => updateRegion(key, Number(e.target.value))}
                        />
                      </label>
                    ))}
                  </div>
                  <small>
                    Vùng chọn: {selectedWidth} × {selectedHeight} px
                  </small>
                </div>
              )}
              {tooSmall && (
                <p className="inline-note amber">
                  Ảnh hoặc vùng chọn quá nhỏ. Mỗi chiều cần ít nhất 224 px.
                </p>
              )}
              {tooLarge && (
                <p className="inline-note amber">
                  Ảnh vượt 12 triệu điểm ảnh. Hãy dùng ảnh có kích thước nhỏ hơn.
                </p>
              )}
            </>
          )}
          <p className="inline-note">
            Chọn rõ vùng da cần kiểm tra để nhận gợi ý bệnh lý và bài viết liên quan. Kết quả chỉ
            mang tính tham khảo, không thay thế chẩn đoán của bác sĩ.
          </p>
          <label className="confirmation-check">
            <input
              type="checkbox"
              checked={saveImage}
              disabled={busy}
              onChange={(e) => setSaveImage(e.target.checked)}
            />
            <span>
              Lưu vùng ảnh đã chọn vào kho riêng để đối chiếu và cho quản trị viên xem, gắn nhãn.
              Ảnh được chuẩn hóa, loại metadata; cần đăng nhập và có thể xóa sau.
            </span>
          </label>
          <button
            className={
              'button primary full image-analyze-button image-analyze-motion ' +
              (busy ? 'is-analyzing' : '')
            }
            disabled={!file || !dimensions.width || busy || tooSmall || tooLarge}
            onClick={() => analyze()}
          >
            {busy ? <LoaderCircle size={18} className="spin" /> : <Focus size={18} />}{' '}
            {busy
              ? 'Đang phân tích và tìm thông tin…'
              : saveImage && !user
                ? 'Đăng nhập để lưu và đối chiếu ảnh'
                : saveImage
                  ? 'Lưu ảnh & phân tích AI'
                  : 'Phân tích ảnh bằng AI'}
          </button>
          {busy && (
            <button
              className="text-button cancel-image-request"
              onClick={() => request.current?.abort('user')}
            >
              Hủy yêu cầu
            </button>
          )}
          {error && (
            <p className="error-text" role="alert">
              {error}
            </p>
          )}
        </section>
        <aside className="image-help">
          <section className="panel photo-guide">
            <span className="guide-icon">
              <Lightbulb size={25} />
            </span>
            <h2>Để ảnh dễ quan sát hơn</h2>
            <ul>
              <li>
                <Sun size={18} />
                <span>Dùng ánh sáng đều, tránh bóng che và phản chiếu.</span>
              </li>
              <li>
                <Focus size={18} />
                <span>Lấy nét vùng cần xem, giữ máy ổn định.</span>
              </li>
              <li>
                <Crop size={18} />
                <span>Giữ một ít vùng da xung quanh, tránh cắt quá sát.</span>
              </li>
              <li>
                <Camera size={18} />
                <span>Dùng ảnh gốc, không dùng bộ lọc làm đẹp hoặc đổi màu.</span>
              </li>
            </ul>
          </section>
          <section className="panel image-model-note">
            <ShieldCheck size={24} />
            <h2>Phạm vi phân tích</h2>
            <p>
              ResNet-18 chạy cục bộ để phân loại nhóm ảnh da liễu. Điểm dưới ngưỡng sẽ không có gợi
              ý. Ảnh ngoài tập huấn luyện vẫn có thể bị phân loại nhầm dù điểm cao.
            </p>
            <p>Kết quả cần được bác sĩ kiểm tra; ảnh mới không tự trở thành ảnh mẫu đã xác nhận.</p>
          </section>
        </aside>
      </div>
      {result && (
        <section className="image-analysis-result" aria-live="polite">
          <div className="results-heading">
            <h2>Kết quả phân tích ảnh</h2>
            <span className="state-badge">
              {result.width} × {result.height} px {result.crop ? '· Vùng đã chọn' : ''}
            </span>
          </div>
          <p className="muted">
            {result.stored
              ? 'Đã lưu ảnh vào kho riêng; gợi ý AI chưa phải nhãn bệnh đã xác nhận.'
              : 'Ảnh không được lưu.'}
          </p>
          <div className="panel image-unified-report">
          {!hasFindings && !hasSupplement && (
            <div className="image-inconclusive">
              <div className="image-inconclusive-heading">
                <Info size={24} aria-hidden="true" />
                <div>
                  <span className="section-kicker">TRẠNG THÁI PHÂN TÍCH</span>
                  <h3>{resultHeading}</h3>
                </div>
              </div>
              <p>{result.fallback?.status === 'unavailable'
                ? 'Hiện chưa thể hoàn tất phân tích ảnh. Vui lòng thử lại sau hoặc tra cứu bằng triệu chứng.'
                : result.message}</p>
              {result.status === 'insufficient_confidence' && (
                <p className="muted">Kết quả này không khẳng định có hay không có bệnh. Hãy thử ảnh đủ sáng, lấy nét rõ vùng da và giữ một ít da xung quanh.</p>
              )}
              {!!result.quality.issues.length && (
                <ul>{result.quality.issues.map((issue) => <li key={issue.code}>{issue.message}</li>)}</ul>
              )}
              <div className="image-inconclusive-actions">
                <button className="button primary" disabled={busy} onClick={() => input.current?.click()}>
                  <Camera size={18} aria-hidden="true" /> Chọn ảnh khác
                </button>
                <button className="button secondary" onClick={symptoms}>Tra cứu bằng triệu chứng <ArrowRight size={17} /></button>
              </div>
            </div>
          )}
          {result.group && !hasSupplement && (
            <div>
              <span className="section-kicker">NHÓM NHÃN DO MÔ HÌNH GỢI Ý</span>
              <h3>{result.group.name}</h3>
              {result.external_sources?.length ? (
                <Reply text={result.message} sources={result.external_sources} />
              ) : (
                <p>{result.message}</p>
              )}
              <p className="muted">
                Điểm nhóm: {result.group.score.toFixed(3)}. {result.score_notice}
              </p>
              <div className="chips">
                {result.related_articles?.map((article) => (
                  <button
                    className="filter-chip"
                    key={article.disease_id}
                    onClick={() => open(article.disease_id)}
                  >
                    Đọc thêm: {article.name}
                  </button>
                ))}
              </div>
            </div>
          )}
          {hasSupplement && result.external_result && (
            <article className="image-report-observations">
              <span className="section-kicker">BÁO CÁO THAM KHẢO</span>
              <h3>Nhận xét từ hình ảnh</h3>
              <Reply text={result.external_result.reply} />
              <p className="muted">Nhận xét chỉ dựa trên hình ảnh, chưa xác nhận chẩn đoán và không thay thế việc khám bệnh.</p>
              {result.external_result.source_reply && <><h4>Thông tin tham khảo</h4><Reply text={result.external_result.source_reply} sources={result.external_result.external_sources} /></>}
              <WebSources sources={result.external_result.external_sources} suggestions={result.external_result.search_suggestions_html} />
            </article>
          )}
          <WebSources
            sources={result.external_sources}
            suggestions={result.search_suggestions_html}
          />
          {result.observations && !hasSupplement && (
            <article>
              <span className="section-kicker">NHẬN XÉT TỪ HỆ THỐNG</span>
              <h3>Dấu hiệu quan sát được</h3>
              <p style={{ whiteSpace: 'pre-wrap' }}>{result.observations}</p>
              {!!result.observation_labels?.length && (
                <div className="chips" aria-label="Nhãn hình thái AI gợi ý">
                  {result.observation_labels.map((l) => (
                    <span className="chip" key={l.id}>
                      {l.name}
                    </span>
                  ))}
                </div>
              )}
              <small className="muted">{result.usage_note}</small>
            </article>
          )}
          {(hasFindings || ['external_result', 'external_observation'].includes(result.external_result?.status || '')) && <button
            className="button primary explain-image-button"
            onClick={() =>
              discuss({
                observations: (result.observations || result.group?.name || '').slice(0, 2000),
                explanation: (result.external_result?.reply || result.message).slice(0, 3000),
                external: ['external_result', 'external_observation'].includes(result.external_result?.status || '') || result.method?.endsWith('-web-fallback'),
                disease_ids: Array.from(
                  new Set([
                    ...(result.candidates || []).map((c) => c.disease_id),
                    ...(result.related_articles || []).map((c) => c.disease_id),
                  ]),
                ).slice(0, 3),
              })
            }
          >
            Trao đổi với AI về kết quả này <ArrowRight size={18} />
          </button>}
          {hasFindings && !hasSupplement && <div className="image-next-step">
            <div>
              <span className="section-kicker">BƯỚC TIẾP THEO</span>
              <h3>
                {result.status === 'research_result'
                  ? 'Bệnh lý tham khảo có trong thư viện'
                  : 'Tìm hiểu thêm từ dấu hiệu'}
              </h3>
              {result.external_sources?.length ? (
                <Reply text={result.message} sources={result.external_sources} />
              ) : (
                <p>{result.message}</p>
              )}
            </div>
            {result.candidates && (
              <div className="image-candidates">
                {result.candidates.map((c) => (
                  <button key={c.disease_id} onClick={() => open(c.disease_id)}>
                    <span>
                      {c.name}
                      <small>
                        {c.english_name} · {c.category} · Nội dung v{c.content_version}
                      </small>
                      <small>{c.summary}</small>
                      {c.photo_scope && (
                        <small>
                          <strong>{c.photo_scope.name}:</strong> {c.photo_scope.note}
                        </small>
                      )}
                      <small>
                        {result.method === 'exact-reference-v1'
                          ? 'Trùng điểm ảnh với ảnh mẫu'
                          : result.method === 'gemini-vision'
                            ? 'Gợi ý tham khảo từ AI'
                            : 'Điểm mô hình: ' + c.score.toFixed(3)}
                      </small>
                      <small>Đọc bài viết và nguồn tham khảo →</small>
                    </span>
                    <ArrowRight size={18} />
                  </button>
                ))}
                <small>{result.score_notice}</small>
                {result.usage_note && <small>{result.usage_note}</small>}
              </div>
            )}
            <button className="button secondary" onClick={symptoms}>
              Tra cứu bằng triệu chứng
              <ArrowRight size={17} />
            </button>
          </div>}
          <SaveButton key={result.image_record_id || result.external_result?.reply || result.message}
            user={user} auth={auth} toast={setSaveNotice} mode="image"
            query={`Phân tích ảnh: ${result.group?.name || result.external_result?.reply || result.observations || result.message}`}
            items={[...(result.candidates || []), ...(result.related_articles || [])].map((item) => ({ id: item.disease_id }))} />
          <small className="muted">Lưu tóm tắt và bài liên quan vào lịch sử; không lưu ảnh gốc.</small>
          {saveNotice && <p role="status">{saveNotice}</p>}
          </div>
        </section>
      )}
      {user && <ImageArchive userId={user.id} refreshKey={String(result?.image_record_id || '')} />}
    </>
  );
}
