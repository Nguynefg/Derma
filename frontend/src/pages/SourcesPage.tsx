import covers from '../shared/data/diseaseCovers.json';
import { ShieldCheck } from 'lucide-react';
import type { Disease } from '../shared/types/index';
import { Heading } from '../shared/components/Heading';
import { DocumentSources } from '../features/library/components/DocumentSources';

export function SourcesPage({ all }: { all: Disease[] }) {
  return (
    <>
      <Heading
        eyebrow="MINH BẠCH TỪ NGUỒN"
        title="Có cơ sở để tìm hiểu."
        description="Đọc bản tóm tắt, kiểm tra tài liệu gốc và nhận biết giới hạn của thông tin."
      />
      <div className="source-intro panel">
        <ShieldCheck size={34} />
        <div>
          <h2>Thư viện có dẫn nguồn</h2>
          <p>
            Nội dung thư viện được tóm tắt từ NIAMS thuộc Viện Y tế Quốc gia Hoa Kỳ (NIH) và NHS của
            Anh. Các bản tiếng Việt chưa được chuyên gia y tế thẩm định. Kho tài liệu có phiên bản
            để truy vết đoạn nội dung được dùng.
          </p>
        </div>
      </div>
      <DocumentSources />
      <section className="panel image-source-list" aria-labelledby="image-source-title">
        <h2 id="image-source-title">Nguồn hình ảnh thư viện</h2>
        <p>
          Ảnh đã được đổi kích thước và chuyển sang WebP. Giấy phép của từng ảnh được ghi bên dưới.
        </p>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Ảnh</th>
                <th>Tác giả</th>
                <th>Nguồn</th>
                <th>Giấy phép</th>
              </tr>
            </thead>
            <tbody>
              {covers.map((cover) => (
                <tr key={cover.key}>
                  <td>{cover.names.join(' / ')}</td>
                  <td>{cover.creator}</td>
                  <td>
                    <a href={cover.sourceUrl} target="_blank" rel="noreferrer">
                      Bản gốc
                    </a>
                  </td>
                  <td>
                    <a href={cover.licenseUrl} target="_blank" rel="noreferrer">
                      {cover.license}
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <div className="panel use-guide">
        <h2>Sử dụng thư viện như thế nào?</h2>
        <div>
          <p>
            <strong>01 · Tìm chủ đề</strong>Nhập câu hỏi hoặc chọn dấu hiệu bạn quan tâm.
          </p>
          <p>
            <strong>02 · Đọc cùng nguồn</strong>Xem đoạn nội dung và mở tài liệu gốc để đối chiếu.
          </p>
          <p>
            <strong>03 · Trao đổi khi cần</strong>Thông tin tham khảo không xác nhận tình trạng sức
            khỏe của bạn.
          </p>
        </div>
      </div>
    </>
  );
}
