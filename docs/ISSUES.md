# DANH MỤC TOÀN BỘ 23 ISSUES DỰ ÁN DERMA LIBRARY

> Trạng thái: dấu hoàn thành cần có minh chứng code/test. Đọc `docs/requirements.md` và `docs/interface-layout.md`; hiệu năng, SQL Server thực tế, giao diện thiết bị và quyền GitHub cần nghiệm thu riêng. Kế hoạch gồm 5 Sprint trong 5 tuần.

> Kế hoạch phân bổ theo **5 Sprint (Milestones)** theo quy trình Agile/Scrum.
> Định dạng chuẩn hóa sẵn sàng nhập vào GitHub Issues, GitLab hoặc Jira.

---

## 🏷️ Quy ước Labels & Priority

| Nhóm | Nhãn (Labels) | Ý nghĩa |
|---|---|---|
| **Loại (Type)** | `type:feature` | Tính năng mới cho người dùng hoặc quản trị |
| | `type:task` | Công việc kỹ thuật, thiết kế hoặc cấu hình |
| | `type:research` | Nghiên cứu dữ liệu, mô hình học máy (AI/ML) |
| | `type:test` | Kiểm thử tự động (Unit / Integration Test) |
| | `type:devops` | Triển khai, CI/CD, kịch bản khởi chạy |
| | `type:documentation` | Tài liệu đặc tả, tài liệu kỹ thuật, báo cáo |
| **Khu vực (Area)** | `area:frontend` | Giao diện React 19, TypeScript, Styling CSS |
| | `area:backend` | FastAPI, REST API, Middleware, Security |
| | `area:database` | Schema CSDL, SQLAlchemy ORM, Migrations, Seed |
| | `area:ai-ml` | PyTorch, ResNet-18, BM25 và trả lời trích xuất cục bộ |
| **Ưu tiên (Priority)**| `priority:high` | Bắt buộc hoàn thành trong sprint |
| | `priority:medium` | Mức độ ưu tiên trung bình |
| | `priority:low` | Tối ưu mở rộng |

---

## 📅 SPRINT 1: PHÂN TÍCH VÀ THIẾT KẾ HỆ THỐNG
*Milestone: Sprint 1 (Tuần 1)*

### `#1` - [DOCS] Khảo sát nghiệp vụ y khoa da liễu & lập tài liệu đặc tả yêu cầu (SRS)
* **Milestone:** Sprint 1
* **Labels:** `type:documentation`, `area:backend`, `priority:high`
* **Mô tả công việc:**
  * Khảo sát nhu cầu thực tế về tra cứu thông tin sức khỏe và bệnh học da liễu bằng tiếng Việt.
  * Xác định rõ phạm vi hệ thống: cung cấp thông tin tham khảo giáo dục sức khỏe, không thay thế chẩn đoán y khoa chuyên sâu.
  * Phân rã chức năng và lập danh sách các module nghiệp vụ: Thư viện bệnh lý, Tra cứu triệu chứng, Kiểm tra ảnh, Hỏi đáp trợ lý, Tài khoản cá nhân và Phân hệ quản trị.
* **Tiêu chí hoàn thành (Acceptance Criteria / DoD):**
  - [x] Có đặc tả phạm vi, tác nhân và 12 Use Case trong `docs/requirements.md`; cần rà soát nghiệm thu yêu cầu với người hướng dẫn.
  - [x] Xác định nguồn dữ liệu tham chiếu chuẩn hóa: ICD-11 của WHO và DermNet.

---

### `#2` - [DATABASE] Thiết kế mô hình dữ liệu quan hệ tổng thể (ERD 13 bảng)
* **Milestone:** Sprint 1
* **Labels:** `type:task`, `area:database`, `priority:high`
* **Mô tả công việc:**
  * Thiết kế kiến trúc CSDL quan hệ gồm 13 bảng dữ liệu đáp ứng toàn bộ các module: người dùng, phiên đăng nhập, bệnh lý, triệu chứng, tài liệu phiên bản, lịch sử tra cứu, nhật ký kiểm toán và kho ảnh.
  * Xác định rõ các mối quan hệ (1-n, n-n) và ràng buộc khóa ngoại (Foreign Keys, Cascade Deletes).
* **Tiêu chí hoàn thành (Acceptance Criteria / DoD):**
  - [x] Hoàn thiện tài liệu `erd-tong-the.md` và sơ đồ thực thể liên kết Mermaid.
  - [x] Xác định khóa chính tự tăng (Identity), trường định danh (slug, uuid), chỉ mục (Index) trên SQL Server và PostgreSQL.

---

### `#3` - [DESIGN] Thiết kế Wireframe & Hệ thống giao diện (Design System)
* **Milestone:** Sprint 1
* **Labels:** `type:task`, `area:frontend`, `priority:medium`
* **Mô tả công việc:**
  * Thiết kế Wireframe/Layout tổng quan cho các màn hình: Trang chủ, Thư viện, Tra cứu triệu chứng, Kiểm tra ảnh, Trợ lý AI, Hồ sơ cá nhân và Quản trị.
  * Xây dựng Design System: tông tím hiện có, bộ typography tiếng Việt chuẩn font Be Vietnam Pro, bảng màu, bộ icon y tế Lucide.
* **Tiêu chí hoàn thành (Acceptance Criteria / DoD):**
  - [ ] Bản vẽ Wireframe layout hoàn chỉnh cho desktop và mobile responsive.
  - [x] Bộ CSS Design Tokens cơ sở trong `frontend/src/shared/styles/`.

---

### `#4` - [DEVOPS] Khởi tạo cấu trúc repository & cấu hình môi trường phát triển
* **Milestone:** Sprint 1
* **Labels:** `type:devops`, `priority:high`
* **Mô tả công việc:**
  * Thiết lập cấu trúc monorepo phân tách rõ ràng (`backend/`, `frontend/`, `research/`, `scripts/`, `docs/`, `storage/`).
  * Cấu hình `.gitignore`, `.dockerignore`, môi trường ảo Python (`.venv`) và cấu hình đóng gói Vite (`package.json`).
* **Tiêu chí hoàn thành (Acceptance Criteria / DoD):**
  - [ ] Khởi tạo Git repo, cấu hình branch protection và quy chuẩn commit.
  - [x] Backend FastAPI khởi chạy thành công endpoint `/api/v1/health`.
  - [x] Frontend React 19 + Vite build thành công không lỗi TypeScript.

---

## 📅 SPRINT 2: XÂY DỰNG CƠ SỞ DỮ LIỆU & THƯ VIỆN BỆNH LÝ
*Milestone: Sprint 2 (Tuần 2)*

### `#5` - [DATABASE] Khởi tạo Database Schema, ORM Models & Migrations
* **Milestone:** Sprint 2
* **Labels:** `type:feature`, `area:backend`, `area:database`, `priority:high`
* **Mô tả công việc:**
  * Cài đặt toàn bộ 13 lớp Declarative Models trong `models.py` bằng SQLAlchemy 2.0 (`tbldiseases`, `tblsymptoms`, `tblusers`,...).
  * Xây dựng module migration tự động (`numeric_ids.py`, `disease_name_index.py`) để nâng cấp cấu trúc bảng an toàn trên cả SQL Server và PostgreSQL.
* **Tiêu chí hoàn thành (Acceptance Criteria / DoD):**
  - [x] Tự động sinh đầy đủ 13 bảng khi backend khởi động.
  - [x] Thiết lập chỉ mục (index) tìm kiếm trên cột `name` của bảng `tbldiseases`.

---

### `#6` - [DATA] Xây dựng công cụ import, chuẩn hóa & dịch dữ liệu ICD-11 WHO
* **Milestone:** Sprint 2
* **Labels:** `type:task`, `area:backend`, `area:database`, `priority:high`
* **Mô tả công việc:**
  * Viết các công cụ tiền xử lý và seed dữ liệu: `seed.py`, `library_expansion.py`, `library_extended.py`, `library_dermnet.py`.
  * Dịch thuật ngữ chương và tên bệnh từ tiếng Anh sang tiếng Việt; chuẩn hóa nhóm bệnh, loại bỏ các mục hoạt chất dược liệu hoặc phân loại hành chính không phải bệnh học.
* **Tiêu chí hoàn thành (Acceptance Criteria / DoD):**
  - [x] Script nạp dữ liệu chạy trơn tru, seed sẵn hàng trăm bài bệnh lý mẫu vào CSDL.
  - [x] Dữ liệu bệnh lý có liên kết đối chiếu với mã định danh quốc tế ICD-11.

---

### `#7` - [BACKEND] Phát triển REST API cho Thư viện bệnh lý (`/api/v1/diseases`)
* **Milestone:** Sprint 2
* **Labels:** `type:feature`, `area:backend`, `priority:high`
* **Mô tả công việc:**
  * Xây dựng controller và routing trong `app/modules/library/routes.py`.
  * Phát triển các endpoints: tìm kiếm theo tên Việt/Anh (không phân biệt dấu), lọc theo chuyên khoa, nhóm chủ đề, hỗ trợ phân trang (pagination) và lấy chi tiết nội dung bài viết.
* **Tiêu chí hoàn thành (Acceptance Criteria / DoD):**
  - [ ] API tìm kiếm bệnh lý phản hồi kết quả < 200ms với phân trang chuẩn.
  - [x] Endpoint chi tiết trả về đầy đủ: tóm tắt, nguyên nhân, nguy cơ, phòng ngừa và danh sách tài liệu tham khảo nguồn (`tblmedical_references`).

---

### `#8` - [FRONTEND] Xây dựng giao diện Thư viện bệnh lý (`LibraryPage.tsx`)
* **Milestone:** Sprint 2
* **Labels:** `type:feature`, `area:frontend`, `priority:high`
* **Mô tả công việc:**
  * Xây dựng trang Thư viện: thanh tìm kiếm với debounce, bộ lọc danh mục theo chuyên khoa (`TopicCard`), lưới hiển thị thẻ bệnh (`DiseaseCard`).
  * Xây dựng modal chi tiết bệnh lý hỗ trợ hiển thị cấu trúc bài viết, hình minh họa trực quan (`SkinIllustration`) và danh mục nguồn trích dẫn (`DocumentSources`).
* **Tiêu chí hoàn thành (Acceptance Criteria / DoD):**
  - [x] Giao diện hiển thị nhanh, responsive trên cả máy tính và điện thoại.
  - [x] Hiển thị chi tiết nội dung bệnh rõ ràng, có phân trang và thông báo khi không tìm thấy kết quả.

---

## 📅 SPRINT 3: TRA CỨU TRIỆU CHỨNG, TÀI KHOẢN, QUẢN TRỊ & DỮ LIỆU ẢNH
*Milestone: Sprint 3 (Tuần 3)*

### `#9` - [FEATURE] Phát triển tính năng tra cứu theo đa triệu chứng (`SymptomPage.tsx`)
* **Milestone:** Sprint 3
* **Labels:** `type:feature`, `area:frontend`, `area:backend`, `priority:high`
* **Mô tả công việc:**
  * Xây dựng logic liên kết nhiều-nhiều qua bảng `tbldisease_symptoms`.
  * Viết API truy vấn đối chiếu đa triệu chứng: tính toán và sắp xếp độ tương đồng dựa trên số lượng dấu hiệu trùng khớp.
  * Xây dựng giao diện chọn triệu chứng trực quan dạng checklist/tag filter trên `SymptomPage.tsx`.
* **Tiêu chí hoàn thành (Acceptance Criteria / DoD):**
  - [x] Người dùng có thể chọn 1 hoặc nhiều triệu chứng cùng lúc để tìm bệnh liên quan.
  - [x] Hiển thị rõ tỷ lệ/số lượng triệu chứng tương ứng và khuyến cáo tham khảo y tế.

---

### `#10` - [AUTH] Xây dựng hệ thống Xác thực, Phân quyền & Quản lý Session
* **Milestone:** Sprint 3
* **Labels:** `type:feature`, `area:backend`, `area:frontend`, `priority:high`
* **Mô tả công việc:**
  * Xây dựng module `app/modules/auth`: Đăng ký, Đăng nhập, Đăng xuất; băm mật khẩu bảo mật (Salt hashing).
  * Quản lý phiên làm việc qua bảng `tblsessions`, xác thực qua HttpOnly Cookie, phòng chống tấn công CSRF bằng CSRF token.
  * Kiểm soát chính sách độ mạnh mật khẩu (`password_policy.py`). Phân quyền người dùng (`user` vs `admin`).
* **Tiêu chí hoàn thành (Acceptance Criteria / DoD):**
  - [x] Đăng nhập/đăng xuất an toàn, tự động hết hạn session khi quá hạn.
  - [x] Bảo vệ an toàn các route nhạy cảm bằng dependency injection (`dependencies.py`).

---

### `#11` - [FEATURE] Cá nhân hóa người dùng: Bài viết đã lưu & Lịch sử tra cứu
* **Milestone:** Sprint 3
* **Labels:** `type:feature`, `area:frontend`, `area:backend`, `priority:medium`
* **Mô tả công việc:**
  * Xây dựng tính năng Bookmark bài viết vào bảng `tblbookmarks` với nút lưu nhanh (`SaveButton.tsx`).
  * Ghi nhận lịch sử tìm kiếm khi người dùng chủ động đồng ý vào bảng `tblsearch_history`.
  * Xây dựng giao diện trang cá nhân (`ProfilePage.tsx`) và trang lịch sử (`HistoryPage.tsx`), cho phép xem lại và xóa lịch sử.
* **Tiêu chí hoàn thành (Acceptance Criteria / DoD):**
  - [x] Người dùng lưu/bỏ lưu bài viết được đồng bộ ngay lập tức.
  - [x] Người dùng có toàn quyền kiểm soát và xóa lịch sử tìm kiếm cá nhân.

---

### `#12` - [ADMIN] Xây dựng Bảng quản trị (CMS) & Quản lý phiên bản tài liệu
* **Milestone:** Sprint 3
* **Labels:** `type:feature`, `area:frontend`, `area:backend`, `priority:high`
* **Mô tả công việc:**
  * Xây dựng giao diện `AdminPage.tsx`:
    - Quản lý danh sách tài khoản người dùng (`AccountManager.tsx`).
    - Biên tập và xuất bản bài viết bệnh lý.
    - Quản lý phiên bản tài liệu y khoa (`DocumentManager.tsx` kết nối `tbldocument_versions`).
    - Ghi nhận nhật ký thao tác quản trị viên vào bảng `tbladmin_audit_logs`.
* **Tiêu chí hoàn thành (Acceptance Criteria / DoD):**
  - [x] Chỉ người dùng có quyền `admin` mới truy cập được phân hệ quản trị.
  - [x] Các thao tác biên tập từ bản cập nhật hiện tại tạo snapshot phiên bản mới kèm checksum SHA-256 (mã băm, không phải chữ ký số).

---

### `#13` - [RESEARCH] Thu thập, làm sạch & chia tập dữ liệu ảnh bệnh lý
* **Milestone:** Sprint 3
* **Labels:** `type:research`, `area:ai-ml`, `priority:high`
* **Mô tả công việc:**
  * Xây dựng các script trong `research/`: `prepare_folders.py`, `prepare_split.py`.
  * Ánh xạ danh mục nhãn bệnh lý (`folder-label-map.json`).
  * Rà soát trùng lặp ảnh bằng mã băm SHA-256 (`pixel_sha256`), phân chia tập dữ liệu Train / Val / Test (tỷ lệ theo từng nguồn; HAM10000 dùng 60:20:20, dữ liệu thư mục tách validation từ train).
* **Tiêu chí hoàn thành (Acceptance Criteria / DoD):**
  - [ ] Đánh giá chồng lặp theo bệnh nhân khi có patient_id; dữ liệu thư mục hiện chưa có thông tin này.
  - [x] Xuất được file manifest mô tả chi tiết phân bố dữ liệu ảnh của từng lớp bệnh.

---

## 📅 SPRINT 4: MÔ HÌNH ẢNH CỤC BỘ (RESNET-18) & HỎI ĐÁP TÀI LIỆU
*Milestone: Sprint 4 (Tuần 4)*

### `#14` - [AI/ML] Huấn luyện mô hình ResNet-18 & Đóng gói Model Card
* **Milestone:** Sprint 4
* **Labels:** `type:research`, `area:ai-ml`, `priority:high`
* **Mô tả công việc:**
  * Huấn luyện mô hình ResNet-18 trên PyTorch/Torchvision bằng kỹ thuật Transfer Learning (`train.py`, `train_frozen.py`).
  * Đo đạc chỉ số: Precision, Recall, F1-Score từng lớp và Confusion Matrix.
  * Đóng gói trọng số thành tệp `.pt` an toàn kèm `model-card.json` định nghĩa ngưỡng tin cậy phân loại (`minimum_score`, `minimum_margin`, `temperature`).
* **Tiêu chí hoàn thành (Acceptance Criteria / DoD):**
  - [x] Hoàn thành báo cáo đánh giá mô hình (ghi nhận trung thực chỉ số Macro-F1 ~31,76%).
  - [x] Đóng gói và kiểm tra tính toàn vẹn bằng SHA-256; đã chạy trọng số thật trên CPU, không tương đương kiểm định lâm sàng.

---

### `#15` - [BACKEND] Xây dựng API kiểm tra và suy luận ảnh da liễu
* **Milestone:** Sprint 4
* **Labels:** `type:feature`, `area:backend`, `area:ai-ml`, `priority:high`
* **Mô tả công việc:**
  * Xây dựng module `app/modules/images/`: tiền xử lý ảnh an toàn qua thư viện Pillow (giới hạn tối đa 12M pixels để chống DoS).
  * Nạp adapter ResNet-18 cục bộ (`image_model.py`) chạy suy luận (CPU/GPU) độc lập không cần internet.
  * Đối chiếu nhãn dự đoán với các thực thể trong CSDL; trả về trạng thái *Chưa xác định* khi dưới ngưỡng tin cậy. Chỉ lưu ảnh vào `tblimage_records` khi người dùng đăng nhập và chọn đồng ý lưu.
* **Tiêu chí hoàn thành (Acceptance Criteria / DoD):**
  - [x] Endpoint `/api/v1/images/analyze` xử lý ảnh và trả về danh sách phân loại nhóm bệnh kèm bài viết liên kết.
  - [x] Kiểm thử từ chối ảnh kém chất lượng, điểm dưới ngưỡng và xử lý nhãn/điểm không hợp lệ.
  - [ ] Đánh giá trên ảnh ngoài phạm vi độc lập; `F:\Dowloads\Data` là bộ train/test hiện có, không phải bộ ảnh lạ. Không bảo đảm nhận biết mọi ảnh ngoài danh mục.

---

### `#16` - [FRONTEND] Phát triển giao diện Kiểm tra hình ảnh (`ImagePage.tsx`)
* **Milestone:** Sprint 4
* **Labels:** `type:feature`, `area:frontend`, `priority:high`
* **Mô tả công việc:**
  * Xây dựng giao diện tải ảnh lên: kéo thả, cắt vùng ảnh, xem trước ảnh.
  * Hiển thị trạng thái và giới hạn mô hình (`ImageModelSummary.tsx`), bài liên quan tới nhóm kết quả và kho ảnh cá nhân (`ImageArchive.tsx`). Không khôi phục các khối bộ lọc nhãn đã được yêu cầu bỏ.
  * Tích hợp nút chuyển ngữ cảnh sang màn hình Trợ lý AI hỏi đáp.
* **Tiêu chí hoàn thành (Acceptance Criteria / DoD):**
  - [x] Người dùng upload ảnh nhận được kết quả dự đoán kèm khuyến cáo y tế rõ ràng.
  - [x] Giao diện cảnh báo trung thực khi mô hình chưa đủ cơ sở nhận diện.

---

### `#17` - [FEATURE] Xây dựng Trợ lý hỏi đáp y khoa dựa trên trích xuất tài liệu
* **Milestone:** Sprint 4
* **Labels:** `type:feature`, `area:backend`, `priority:high`
* **Mô tả công việc:**
  * Xây dựng module `app/modules/assistant`: logic tìm kiếm đoạn trích ngữ cảnh từ kho tài liệu đã xuất bản (`tblmedical_documents`).
  * Ưu tiên BM25 và đoạn trích nội bộ; khi không có tài liệu phù hợp và người dùng cho phép, gọi Gemini có Google Search và tách riêng nguồn web.
  * Chỉ dùng các đoạn trích có nguồn; thông báo chưa có thông tin nếu tài liệu thư viện không đề cập.
* **Tiêu chí hoàn thành (Acceptance Criteria / DoD):**
  - [x] Câu trả lời kèm đoạn trích và liên kết nguồn tài liệu xuất bản.
  - [x] Kiểm thử câu hỏi không có nguồn, câu hỏi tiếp nối, phiên bản tài liệu hiện tại và đoạn trích nguyên văn. Nội dung nguồn vẫn cần thẩm định chuyên môn.

---

### `#18` - [FRONTEND] Xây dựng giao diện Trợ lý AI hỏi đáp (`QuestionPage.tsx`)
* **Milestone:** Sprint 4
* **Labels:** `type:feature`, `area:frontend`, `priority:high`
* **Mô tả công việc:**
  * Phát triển component chat trực tuyến `AssistantChat.tsx`: hiển thị luồng tin nhắn hai chiều giữa người dùng và trợ lý, hiệu ứng đang phản hồi, hỗ trợ hiển thị Markdown.
  * Hiển thị danh sách các nguồn tài liệu trích dẫn đi kèm phía dưới mỗi câu trả lời.
  * Cung cấp câu hỏi gợi ý về thư viện; chuyển ngữ cảnh bài liên quan từ kết quả ảnh sang hội thoại.
* **Tiêu chí hoàn thành (Acceptance Criteria / DoD):**
  - [x] Giao diện trò chuyện mượt mà, thân thiện, lưu lịch sử chat trong phiên làm việc.
  - [x] Người dùng có thể nhấn vào nguồn tài liệu trích dẫn để đọc bài viết gốc.

---

## 📅 SPRINT 5: KIỂM THỬ, TỐI ƯU VÀ HOÀN THIỆN SẢN PHẨM
*Milestone: Sprint 5 (Tuần 5)*

### `#19` - [TEST] Xây dựng bộ kiểm thử tự động Backend (Pytest)
* **Milestone:** Sprint 5
* **Labels:** `type:test`, `area:backend`, `priority:high`
* **Mô tả công việc:**
  * Viết bộ test cases tự động bằng `pytest` trong thư mục `backend/tests/`:
    - Test các endpoints tra cứu bệnh lý, lọc triệu chứng, phân trang.
    - Test quy trình đăng nhập, session, CSRF token và phân quyền admin.
    - Test kiểm tra tính hợp lệ của tệp ảnh tải lên và nạp model adapter.
* **Tiêu chí hoàn thành (Acceptance Criteria / DoD):**
  - [x] Bộ test hiện tại: 200 passed, 2 skipped cho script đã nghỉ sử dụng; xem `docs/sprint-review.md`.
  - [ ] Kiểm tra đầy đủ các mã lỗi trả về (400, 401, 403, 404, 502, 503).

---

### `#20` - [PERF] Tối ưu hóa hiệu năng tải trang & truy vấn CSDL
* **Milestone:** Sprint 5
* **Labels:** `type:task`, `area:frontend`, `area:backend`, `priority:medium`
* **Mô tả công việc:**
  * Kích hoạt middleware nén dữ liệu `PublicCompression` (gzip) trên backend.
  * Cấu hình nạp lười (`React.lazy` và `Suspense`) cho toàn bộ các trang chức năng trên frontend để giảm kích thước bundle ban đầu.
  * Tinh chỉnh chỉ mục index trên cơ sở dữ liệu để tối ưu tốc độ truy vấn danh mục bệnh.
* **Tiêu chí hoàn thành (Acceptance Criteria / DoD):**
  - [ ] Điểm First Contentful Paint (FCP) dưới 1.5 giây.
  - [ ] API tìm kiếm bệnh lý phản hồi trung bình dưới 200ms.

---

### `#21` - [SECURITY] Rà soát và gia cố an ninh hệ thống
* **Milestone:** Sprint 5
* **Labels:** `type:task`, `area:backend`, `priority:high`
* **Mô tả công việc:**
  * Kiểm tra hoạt động của middleware `BoundedBody` (giới hạn kích thước payload).
  * Rà soát cơ chế giới hạn phân tích ảnh `Image.MAX_IMAGE_PIXELS = 12_000_000` để chống tấn công Image Bomb DoS.
  * Kiểm tra cấu hình `COOKIE_SECURE`, CORS `ALLOWED_ORIGINS` và ẩn toàn bộ API Key trên máy chủ.
* **Tiêu chí hoàn thành (Acceptance Criteria / DoD):**
  - [ ] Hệ thống chặn đứng các request vượt quá giới hạn hoặc giả mạo header.
  - [ ] Tuyệt đối không để lộ thông tin nhạy cảm, API key hoặc dấu vết hệ thống trong logs.

---

### `#22` - [DEVOPS] Hoàn thiện kịch bản khởi chạy 1-chạm & Docker Compose
* **Milestone:** Sprint 5
* **Labels:** `type:devops`, `priority:high`
* **Mô tả công việc:**
  * Hoàn thiện kịch bản khởi chạy tự động trên Windows (`start.cmd`, `scripts/start.cmd`, `scripts/start.ps1`): tự động kiểm tra Node.js 22+, Python 3.11+, khởi tạo `.venv`, cài đặt dependencies, build React và chạy Uvicorn.
  * Hoàn thiện cấu hình `Dockerfile` và `compose.yaml` phục vụ triển khai môi trường container hóa.
* **Tiêu chí hoàn thành (Acceptance Criteria / DoD):**
  - [ ] Chạy lệnh `.\start.cmd` trên môi trường sạch tự động khởi động thành công website tại `http://127.0.0.1:8000`.
  - [ ] Khởi chạy thành công ứng dụng qua lệnh `docker compose up`.

---

### `#23` - [DOCS] Hoàn thiện tài liệu nghiệm thu, Slide báo cáo & Kịch bản Demo
* **Milestone:** Sprint 5
* **Labels:** `type:documentation`, `priority:high`
* **Mô tả công việc:**
  * Cập nhật hoàn thiện tệp `README.md` hướng dẫn chi tiết cách cài đặt, cấu hình cơ sở dữ liệu và vận hành hệ thống.
  * Soạn thảo kịch bản demo tính năng hoàn chỉnh: Tra cứu thư viện -> Chọn đa triệu chứng -> Tải ảnh phân loại ResNet-18 -> Hỏi đáp với Trợ lý AI -> Đăng nhập & Quản trị.
  * Chuẩn bị tài liệu báo cáo nghiệm thu đồ án và slide thuyết trình.
* **Tiêu chí hoàn thành (Acceptance Criteria / DoD):**
  - [x] Tài liệu mô tả đầy đủ các bước cài đặt và vận hành hệ thống.
  - [ ] Kịch bản demo chạy thông suốt, không phát sinh lỗi trong quá trình trình diễn.

## Minh chứng sau rà soát

Xem `docs/sprint-review.md` để phân biệt thay đổi đã kiểm thử với các điều kiện nghiệm thu còn cần môi trường thật.

## Minh chứng Sprint 4

Xem `docs/sprint4-result.md`. Phần triển khai đã có kiểm thử tự động và chạy trọng số thật; kiểm chứng ảnh ngoài phạm vi thực tế còn chờ bộ ảnh độc lập.

## Bổ sung luồng Gemini dự phòng

Theo yêu cầu mới: model cục bộ và CSDL được ưu tiên; khi thiếu bài/tài liệu và người dùng cho phép, sử dụng Gemini/Google Search. Xem `docs/hybrid-ai.md`. Kết nối thật hiện bị giới hạn quota/rate limit 429 nên chưa nghiệm thu phản hồi web thật.
