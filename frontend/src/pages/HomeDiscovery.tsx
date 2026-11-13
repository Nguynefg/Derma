import { useState } from 'react';
import {
  Activity, ArrowRight, ArrowUpRight, Bone, BookOpen, Brain, Droplets,
  Ear, Fingerprint, HeartPulse, Layers3, ScanLine, Search, ShieldCheck,
  Sparkles, Stethoscope, Utensils, Wind,
} from 'lucide-react';
import './HomeDiscovery.css';

type Destination = 'questions' | 'symptoms' | 'images' | 'sources' | 'library';
const specialtyIcons: Record<string, typeof BookOpen> = {
  'Cơ xương khớp': Bone, 'Da liễu': Fingerprint, 'Hô hấp': Wind,
  'Nội tiết': Activity, 'Tai mũi họng': Ear, 'Thận & tiết niệu': Droplets,
  'Thần kinh': Brain, 'Tiêu hóa': Utensils, 'Tim mạch': HeartPulse, 'Khác': Layers3,
};
const paths = [
  { page: 'symptoms', icon: Stethoscope, title: 'Từ triệu chứng', description: 'Chọn dấu hiệu bạn đang gặp' },
  { page: 'images', icon: ScanLine, title: 'Từ hình ảnh', description: 'Tham khảo ảnh da liễu' },
  { page: 'questions', icon: Sparkles, title: 'Từ một câu hỏi', description: 'Trao đổi cùng trợ lý AI' },
] as const;

export function HomeDiscovery({ specialties, search, browse, navigate }: {
  specialties: string[];
  search: (query: string) => void;
  browse: (specialty: string) => void;
  navigate: (page: Destination) => void;
}) {
  const [query, setQuery] = useState('');
  return (
    <div className="home-discovery">
      <section className="discovery-hero" aria-labelledby="discovery-title">
        <div className="discovery-copy">
          <span className="discovery-eyebrow"><span /> THƯ VIỆN SỨC KHỎE ĐA CHUYÊN KHOA</span>
          <h1 id="discovery-title">Thông tin sức khỏe,<br /><span>dễ tìm, dễ hiểu.</span></h1>
          <p>Tìm hiểu bệnh lý bằng tiếng Việt. Bắt đầu từ một tên bệnh, một dấu hiệu hoặc điều bạn đang băn khoăn.</p>
          <form className="discovery-search" onSubmit={event => { event.preventDefault(); search(query.trim()); }}>
            <Search size={20} aria-hidden="true" />
            <input value={query} maxLength={300} onChange={event => setQuery(event.target.value)} aria-label="Tìm tên bệnh hoặc từ khóa" placeholder="Bạn muốn tìm hiểu điều gì?" />
            <button type="submit" aria-label="Tìm kiếm trong thư viện"><span>Tìm kiếm</span><ArrowRight size={18} aria-hidden="true" /></button>
          </form>
          <div className="discovery-suggestions"><span>Thử tìm</span>{['Viêm da cơ địa', 'Hen phế quản', 'Đái tháo đường'].map(value => <button key={value} onClick={() => search(value)}>{value}<ArrowUpRight size={12} aria-hidden="true" /></button>)}</div>
        </div>
        <div className="discovery-visual">
          <div className="discovery-halo" aria-hidden="true" />
          <div className="discovery-book" aria-hidden="true">
            <span className="discovery-book-tag">DERMA / THƯ VIỆN</span>
            <BookOpen size={88} strokeWidth={1.1} />
            <strong>Sức khỏe.<br />Hiểu thêm mỗi ngày.</strong>
            <span className="discovery-book-rule" />
          </div>
          <button className="discovery-source-card" onClick={() => navigate('sources')}>
            <span><ShieldCheck size={23} aria-hidden="true" /></span>
            <span><strong>Đọc cùng nguồn tham khảo</strong><small>Mở tài liệu để đối chiếu thông tin</small></span>
            <ArrowUpRight size={16} aria-hidden="true" />
          </button>
        </div>
      </section>
      <nav className="discovery-paths" aria-label="Các cách tra cứu">
        {paths.map(({page, icon: Icon, title, description}) => <button key={page} onClick={() => navigate(page)}><span className="discovery-path-icon"><Icon size={22} aria-hidden="true" /></span><span><strong>{title}</strong><small>{description}</small></span><ArrowRight size={18} aria-hidden="true" /></button>)}
      </nav>
      <p className="discovery-notice"><ShieldCheck size={15} aria-hidden="true" />Thông tin hỗ trợ tìm hiểu, không thay thế việc khám và chẩn đoán của bác sĩ.</p>
      <section className="discovery-directory" aria-labelledby="directory-title">
        <header><div><span className="discovery-eyebrow">TÌM THEO LĨNH VỰC</span><h2 id="directory-title">Khám phá theo chuyên khoa</h2></div><button onClick={() => browse('')}>Xem tất cả<ArrowRight size={17} aria-hidden="true" /></button></header>
        <div className="discovery-specialties">
          {specialties.map(name => { const Icon = specialtyIcons[name] || Stethoscope; return <button key={name} onClick={() => browse(name)}><span><Icon size={23} strokeWidth={1.6} aria-hidden="true" /></span><strong>{name}</strong><ArrowUpRight size={15} aria-hidden="true" /></button>; })}
        </div>
      </section>
    </div>
  );
}
