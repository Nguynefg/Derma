import {
  ArrowRight,
  BookOpen,
  Search,
  ShieldCheck,
} from 'lucide-react';
import type { Disease } from '../shared/types/index';
import { HomeDiscovery } from './HomeDiscovery';
import { TopicCard } from '../features/library/components/TopicCard';
import { LoadingSkeleton } from '../shared/components/Visuals';

type Props = {
  diseases: Disease[];
  browse: (specialty: string) => void;
  search: (query: string) => void;
  navigate: (page: 'questions' | 'symptoms' | 'images' | 'sources' | 'library') => void;
  open: (disease: Disease) => void;
  loading?: boolean;
  loadError?: string;
  retry?: () => void;
};

export function HomePage({ diseases, search, browse, navigate, open, loading, loadError, retry }: Props) {
  const featured = ['atopic-dermatitis', 'asthma', 'type-2-diabetes']
    .map((id) => diseases.find((d) => d.slug === id))
    .filter((d): d is Disease => Boolean(d));
  const topics = featured.length ? featured : diseases.slice(0, 3);
  const specialties = [...new Set(diseases.map(d => d.specialty).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'vi'));
  return (
    <div className="home-page">
      <HomeDiscovery specialties={specialties} search={search} browse={browse} navigate={navigate} />
      <section className="landing-section home-library-section">
        <div className="section-heading split-heading">
          <div>
            <span className="section-kicker">THƯ VIỆN BỆNH LÝ</span>
            <h2>
              Đọc thêm từ thư viện
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
          <h2>Hiểu rõ cách <span>Derma hoạt động.</span></h2>
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

