# Rà soát dự án Derma — 13/11/2026

## Phạm vi và cách kiểm tra

- Kiểm tra cấu trúc frontend, backend, scripts, research, cấu hình khởi chạy và workflow GitHub.
- Phân tích cú pháp 171 file Python trong backend/app, backend/tests, scripts và research: không có lỗi cú pháp.
- Đọc các luồng chính: xác thực, CSRF, phân quyền quản trị, thư viện, tài liệu, lịch sử, ảnh và trợ lý.
- Không sửa dữ liệu thật, không huấn luyện lại model, không gọi Gemini trả phí, không commit/push GitHub.
- Đây là kiểm tra kỹ thuật có giới hạn, không phải kiểm định an ninh toàn diện hoặc thẩm định chuyên môn y khoa.

## Lỗi đã sửa trong lần rà soát này

1. **Kho tài liệu tải toàn bộ danh sách dù chỉ hiển thị 10 dòng.**
   Thêm API quản trị `/api/v1/admin/documents-page`, phân trang tại CSDL, mặc định 10 mục; frontend dùng API mới. API danh sách cũ được giữ để tương thích. Có thứ tự ổn định theo title và ID, kiểm tra giới hạn trang và quyền admin.
2. **Phản hồi tải tài liệu cũ có thể ghi đè trang đang xem.**
   Frontend bỏ phản hồi cũ bằng số thứ tự yêu cầu; bổ sung trạng thái tải, thử lại và danh sách trống.
3. **Thông báo xác thực đầu vào có thể hiển thị “undefined ký tự”.**
   Backend chủ động không phản hồi validator context để tránh lộ dữ liệu. Frontend nay dùng thông báo ngắn/dài chung nếu không có giới hạn cụ thể.
4. **Workflow GitHub dùng mẫu không khớp dự án.**
   Workflow chính nay chạy Python 3.12 với requirements thật và bộ kiểm thử backend; job riêng dùng Node 22, npm ci và build frontend. Hai mẫu phát hành PyPI/SLSA được chuyển vào `docs/architecture/workflow-templates/*.example`; không tự chạy phát hành khi tạo release. Chưa chạy workflow trên GitHub từ phiên này.
5. **Thiếu `.env.example` dù tài liệu đề cập.**
   Thêm mẫu cấu hình, để trống khóa bí mật, giữ cơ chế cấu hình SQL Server hiện có.
6. **Môi trường .venv thiếu Pygments, phụ thuộc của pytest.**
   Bổ sung vào môi trường cục bộ; kiểm tra phụ thuộc biệt lập sau đó không báo xung đột. Không thay môi trường Python toàn máy hoặc .venv-research.

## Kết quả xác minh

| Kiểm tra | Kết quả |
|---|---|
| Toàn bộ backend/tests sau thay đổi backend | 235 passed, 2 skipped, 1 warning; 29,50 giây |
| Frontend TypeScript + Vite | Build thành công |
| npm audit | 0 lỗ hổng được báo cáo tại thời điểm kiểm tra |
| pip check chỉ với thư viện .venv | No broken requirements found |
| Quét mẫu khóa bí mật trong 438 file được Git theo dõi | Không tìm thấy mẫu khóa đã kiểm tra; không thay thế quét mọi loại bí mật hoặc toàn bộ lịch sử Git |
| Theo dõi .env, database.local.json, model, storage trong Git | Không có file thuộc các đường dẫn được kiểm tra |
| Trình duyệt Chrome headless, API giả lập | 7 kiểm tra đạt, không có lỗi JavaScript được ghi nhận |

Hai bài bị bỏ qua thuộc script cũ không còn sử dụng; một cảnh báo là Starlette đang khuyến nghị thay httpx trong TestClient. Không coi bài bỏ qua là bài đã đạt.

Kiểm tra trình duyệt gồm: lưu tra cứu thư viện, hiển thị lịch sử, phân trang tài liệu 10 mục và chuyển trang, một báo cáo ảnh không hiện tên nhà cung cấp/lỗi kỹ thuật, lưu tóm tắt ảnh khi không có bài liên quan, màn hình 390px không tràn ngang. Dữ liệu giả lập chỉ chứng minh luồng giao diện; API thực được kiểm thử riêng trên SQLite tạm.

Ảnh chụp và kết quả chạy nằm tại `storage/exports/project-audit-20261113/`. File browser-result.json ghi rõ các trường hợp đạt.

## Luồng lưu lịch sử đã xác minh lại

- Thư viện và triệu chứng: người dùng chủ động bấm “Đồng ý lưu tra cứu”.
- Phân tích ảnh: nút lưu ghi tóm tắt tối đa 300 ký tự và mã bài liên quan, không lưu toàn bộ báo cáo hoặc ảnh gốc.
- Lưu ảnh vào kho riêng và lưu lượt tra cứu là hai thao tác khác nhau.
- Backend yêu cầu đăng nhập, CSRF và consent=true; lịch sử được đọc theo user_id hiện tại.
- Các lượt chưa từng lưu không được tự khôi phục hoặc thêm vào lịch sử.

## Chưa xác minh được hoặc còn hạn chế

- **SQL Server thật:** truy vấn chỉ đọc vẫn nhận OperationalError. Chưa xác minh schema, index, tổng số bản ghi và thao tác lưu trên SQL Server thật trong lần này. Con số 15.439 là từ bản kiểm kê người dùng đã xuất, không phải truy vấn trực tiếp mới.
- **Gemini và Google Search:** không kiểm tra dịch vụ thật trong lần này. Các tình huống kỹ thuật có test giả lập; không kết luận quota đã phục hồi.
- **Model ảnh:** không huấn luyện hay đánh giá lại; chỉ số accuracy khoảng 34,6% vẫn là kết quả cũ. Chưa có đánh giá trên bộ ảnh ngoài phạm vi độc lập đủ để kết luận khả năng từ chối ảnh lạ.
- **Ảnh minh họa:** mới có 20 ảnh riêng gắn cho 23 bản ghi trong bản kiểm kê; còn 15.416 bản ghi cần bổ sung/thay ảnh. Các ảnh sinh AI không phải ảnh lâm sàng và không đưa vào bộ train.
- **Nội dung bệnh lý:** chưa thẩm định y khoa hoặc kiểm tra lại toàn bộ nội dung tiếng Việt trên CSDL thật.
- **Triển khai:** chưa nghiệm thu Docker hoặc cài mới trên máy sạch; phiên này không có lệnh Docker để chạy. Cấu hình Compose hiện dùng PostgreSQL, khác môi trường SQL Server trên Windows.
- **Bảo mật vận hành:** rate limit hiện lưu trong bộ nhớ một tiến trình; cần kho giới hạn dùng chung khi chạy nhiều worker. Cookie Secure phải bật khi triển khai HTTPS. Chưa chạy kiểm toán lỗ hổng dependency backend hoặc kiểm thử xâm nhập độc lập; npm audit chỉ áp dụng frontend.
- **Khởi động lại:** thay đổi backend yêu cầu restart web. Không chạy lại các lệnh nhập, xóa hoặc đồng bộ dữ liệu chỉ để cập nhật giao diện.

## Thứ tự nên hoàn thiện tiếp

1. Kiểm thử lưu/đọc lịch sử và phân trang trên SQL Server thật sau khi khởi động lại web.
2. Bổ sung ảnh kiểm thử ngoài phạm vi độc lập; đo chất lượng model trước khi tăng mức sử dụng thực tế.
3. Tiếp tục ảnh minh họa và rà soát nội dung theo từng đợt, ghi số lượng thực tế.
4. Nghiệm thu CI trên GitHub, cài mới Windows và Docker tách biệt trước triển khai.
