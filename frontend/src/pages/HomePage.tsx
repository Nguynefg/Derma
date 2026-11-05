import { useState } from 'react';
import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  ScanLine,
  Search,
  ShieldCheck,
  Sparkles,
  Stethoscope,
} from 'lucide-react';
import type { Disease } from '../shared/types/index';
import { TopicCard } from '../features/library/components/TopicCard';
import { KnowledgeArtwork } from '../shared/components/KnowledgeArtwork';
import { LoadingSkeleton } from '../shared/components/Visuals';

type Props = {
  diseases: Disease[];
  search: (query: string) => void;
  navigate: (page: 'questions' | 'symptoms' | 'images' | 'sources' | 'library') => void;
  open: (disease: Disease) => void;
  loading?: boolean;
  loadError?: string;
  retry?: () => void;
};

export function HomePage({ diseases, search, navigate, open, loading, loadError, retry }: Props) {
  const [query, setQuery] = useState('');
  const featured = ['atopic-dermatitis', 'asthma', 'type-2-diabetes']
    .map((id) => diseases.find((d) => d.slug === id))
    .filter((d): d is Disease => Boolean(d));
  const topics = featured.length ? featured : diseases.slice(0, 3);
  return (
    <div className="home-page">
      <section className="discover-hero">
        <div className="discover-copy">
          <span className="discover-eyebrow">
            <span /> MỘT NƠI ĐỂ HIỂU THÊM VỀ SỨC KHỎE
          </span>
          <h1>
            Hiểu sức khỏe.
            <br />
            <em>Chạm tới an tâm.</em>
          </h1>
          <p>
            Khám phá kiến thức sức khỏe bằng tiếng Việt. Tìm một chủ đề, nhận biết dấu hiệu và hỏi
            thêm khi bạn cần.
          </p>
          <form
            className="discover-search"
            onSubmit={(event) => {
              event.preventDefault();
              search(query);
            }}
          >
            <Search size={22} aria-hidden="true" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              maxLength={300}
              placeholder="Tìm tên bệnh, triệu chứng…"
              aria-label="Tìm tên bệnh hoặc từ khóa"
            />
            <button type="submit" aria-label="Tìm kiếm trong thư viện">
              <ArrowRight size={22} />
            </button>
          </form>
          <div className="discover-suggestions">
            <span>Thử tìm</span>
            {['Viêm da cơ địa', 'Mụn trứng cá', 'Vảy nến'].map((value) => (
              <button key={value} onClick={() => search(value)}>
                {value}
                <ArrowUpRight size={13} />
              </button>
            ))}
          </div>
          <div className="discover-trust">
            <ShieldCheck size={17} />
            <span>Có nguồn để đối chiếu</span>
            <i />
            <BookOpen size={17} />
            <span>Đọc theo cách của bạn</span>
          </div>
        </div>
        <div className="discover-visual">
          <KnowledgeArtwork />
          <div className="discover-paths">
            <button onClick={() => navigate('symptoms')}>
              <span className="path-symbol mint">
                <Stethoscope size={21} />
              </span>
              <span>
                <strong>Từ một dấu hiệu</strong>
                <small>Khám phá triệu chứng</small>
              </span>
              <ArrowUpRight size={18} />
            </button>
            <button onClick={() => navigate('questions')}>
              <span className="path-symbol lilac">
                <Sparkles size={21} />
              </span>
              <span>
                <strong>Từ một câu hỏi</strong>
                <small>Trò chuyện cùng AI</small>
              </span>
              <ArrowUpRight size={18} />
            </button>
          </div>
        </div>
      </section>
      <div className="discover-footnote">
        <InfoMark /> Thông tin tham khảo giúp bạn tìm hiểu, không thay thế bác sĩ chẩn đoán.
      </div>

      <div className="mosaic-heading">
        <span className="section-kicker">KHÁM PHÁ THEO CÁCH CỦA BẠN</span>
        <h2>Bắt đầu từ đâu cũng được.</h2>
      </div>
      <section className="feature-mosaic" aria-label="Chọn cách khám phá">
        <button className="mosaic-card mosaic-assistant" onClick={() => navigate('questions')}>
          <span className="mosaic-topline">
            <span>GÓC TRÒ CHUYỆN</span>
            <ArrowUpRight size={22} />
          </span>
          <div className="mosaic-orb" aria-hidden="true">
            <Sparkles size={46} strokeWidth={1.2} />
            <i />
            <i />
          </div>
          <div>
            <h2>
              Hỏi điều bạn nghĩ.
              <br />
              Hiểu điều bạn cần.
            </h2>
            <p>Một cuộc trò chuyện để cùng bạn tìm hiểu sức khỏe.</p>
          </div>
          <span className="mosaic-cta">
            Trò chuyện cùng trợ lý <ArrowRight size={17} />
          </span>
        </button>
        <button className="mosaic-card mosaic-images" onClick={() => navigate('images')}>
          <span className="mosaic-topline">
            <span>KHÁM PHÁ BẰNG ẢNH</span>
            <ArrowUpRight size={22} />
          </span>
          <div className="mosaic-scan" aria-hidden="true">
            <div />
            <ScanLine size={62} strokeWidth={1} />
            <span />
          </div>
          <div>
            <h2>
              Thêm một
              <br />
              góc nhìn.
            </h2>
            <p>Quan sát dấu hiệu trên ảnh da và tìm bài viết tham khảo.</p>
          </div>
          <span className="mosaic-cta">
            Chọn hình ảnh <ArrowRight size={17} />
          </span>
        </button>
        <button className="mosaic-card mosaic-symptoms" onClick={() => navigate('symptoms')}>
          <span className="mosaic-topline">
            <span>LẮNG NGHE CƠ THỂ</span>
            <ArrowUpRight size={22} />
          </span>
          <div className="mosaic-pulse" aria-hidden="true">
            <Stethoscope size={70} strokeWidth={1} />
            <span>01</span>
            <span>02</span>
          </div>
          <div>
            <h2>
              Từ những
              <br />
              dấu hiệu nhỏ.
            </h2>
            <p>Chọn điều bạn nhận thấy để khám phá nội dung liên quan.</p>
          </div>
          <span className="mosaic-cta">
            Tra cứu triệu chứng <ArrowRight size={17} />
          </span>
        </button>
      </section>

      <section className="landing-section home-library-section">
        <div className="section-heading split-heading">
          <div>
            <span className="section-kicker">THƯ VIỆN BỆNH LÝ</span>
            <h2>
              Thông tin bạn có thể
              <br />
              <span>đọc và đối chiếu.</span>
            </h2>
            <p>Các bản tóm tắt ngắn kèm liên kết đến nguồn tham khảo.</p>
          </div>
          <button className="button secondary" onClick={() => search('')}>
            Khám phá thư viện <ArrowRight size={18} />
          </button>
        </div>
        {loading ? (
          <LoadingSkeleton />
        ) : loadError ? (
          <div className="empty" role="status">
            <p>{loadError}</p>
            <button className="button secondary" onClick={retry}>
              Tải lại bài viết
            </button>
          </div>
        ) : (
          <div className="disease-grid home-grid">
            {topics.map((d, i) => (
              <TopicCard key={d.id} disease={d} index={i} open={() => open(d)} />
            ))}
          </div>
        )}
      </section>

      <section className="how-section landing-section">
        <div className="section-heading centered">
          <span className="section-kicker">ĐƠN GIẢN TỪ BƯỚC ĐẦU TIÊN</span>
          <h2>
            Tìm hiểu có cơ sở,
            <br />
            <span>theo từng bước.</span>
          </h2>
        </div>
        <div className="how-grid">
          <article>
            <span className="how-step-icon" aria-hidden="true">
              <Search size={25} />
            </span>
            <span className="how-number">01</span>
            <h3>Tìm điều bạn quan tâm</h3>
            <p>Nhập từ khóa, chọn dấu hiệu hoặc đặt câu hỏi trong phạm vi thư viện.</p>
          </article>
          <article>
            <span className="how-step-icon" aria-hidden="true">
              <BookOpen size={25} />
            </span>
            <span className="how-number">02</span>
            <h3>Đọc cùng tài liệu nguồn</h3>
            <p>Xem nội dung liên quan, mở tài liệu gốc và nhận biết giới hạn của thông tin.</p>
          </article>
          <article>
            <span className="how-step-icon" aria-hidden="true">
              <ShieldCheck size={25} />
            </span>
            <span className="how-number">03</span>
            <h3>Chủ động lựa chọn</h3>
            <p>Lưu tra cứu khi bạn đồng ý và trao đổi với nhân viên y tế khi cần.</p>
          </article>
        </div>
      </section>

      <section className="landing-section faq-section">
        <div className="section-heading">
          <span className="section-kicker">TRƯỚC KHI BẠN BẮT ĐẦU</span>
          <h2>
            Hiểu rõ cách
            <br />
            <span>Derma hoạt động.</span>
          </h2>
        </div>
        <div className="faq-list">
          <details>
            <summary>
              Derma có chẩn đoán bệnh không?<span>+</span>
            </summary>
            <p>
              Derma hỗ trợ tra cứu thông tin. Kết quả không xác nhận bạn mắc bệnh và không thay thế
              việc khám với nhân viên y tế.
            </p>
          </details>
          <details>
            <summary>
              Thông tin được lấy từ đâu?<span>+</span>
            </summary>
            <p>
              Kho thư viện có các bản tóm tắt từ NIAMS thuộc NIH và NHS, kèm liên kết đến tài liệu
              gốc. Bản tiếng Việt chưa được chuyên gia y tế thẩm định.
            </p>
            <button className="text-button" onClick={() => navigate('sources')}>
              Xem nguồn tham khảo <ArrowRight size={17} />
            </button>
          </details>
          <details>
            <summary>
              Lịch sử có tự động được lưu không?<span>+</span>
            </summary>
            <p>
              Không. Bạn cần đăng nhập và chủ động chọn đồng ý lưu từng lượt tra cứu. Bạn có thể xóa
              các mục đã lưu trong trang lịch sử.
            </p>
          </details>
          <details>
            <summary>
              Ảnh tải lên có được nhận diện bệnh không?<span>+</span>
            </summary>
            <p>
              Bạn có thể chọn vùng ảnh để AI mô tả dấu hiệu và gợi ý chủ đề liên quan trong thư
              viện. Ảnh chỉ được lưu khi bạn đăng nhập và chọn lưu. Kết quả là thông tin tham khảo,
              không xác nhận chẩn đoán; bạn có thể chuyển kết quả sang trợ lý để hỏi thêm.
            </p>
          </details>
        </div>
      </section>

      <section className="landing-cta">
        <div>
          <span className="section-kicker">BẮT ĐẦU TÌM HIỂU</span>
          <h2>
            Một câu hỏi nhỏ.
            <br />
            Một bước hiểu thêm.
          </h2>
          <p>Tra cứu trong kho tài liệu và xem những thông tin có nguồn.</p>
        </div>
        <button className="button light" onClick={() => navigate('questions')}>
          Đặt câu hỏi của bạn <ArrowRight size={20} />
        </button>
        <span className="cta-spark" aria-hidden="true">
          ✳
        </span>
      </section>
    </div>
  );
}

function InfoMark() {
  return (
    <span className="hero-info-mark" aria-hidden="true">
      i
    </span>
  );
}
