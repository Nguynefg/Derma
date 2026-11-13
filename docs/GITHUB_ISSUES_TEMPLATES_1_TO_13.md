# NỘI DUNG MẪU 13 ISSUES GITHUB (SPRINT 1 - SPRINT 3)

> Trạng thái: dấu hoàn thành cần có minh chứng code/test. Đọc `docs/requirements.md` và `docs/interface-layout.md`; hiệu năng, SQL Server thực tế, giao diện thiết bị và quyền GitHub cần nghiệm thu riêng. Kế hoạch gồm 5 Sprint trong 5 tuần.
DỰ ÁN: DERMA LIBRARY

Dùng để copy-paste trực tiếp vào ô Description của từng Issue trên GitHub.

=============================================================================
ISSUE #1
Title: [DOCS] Khảo sát nghiệp vụ y khoa da liễu & lập tài liệu đặc tả yêu cầu (SRS)
Milestone: Sprint 1
Labels: type:documentation, area:backend, priority:high
-----------------------------------------------------------------------------
### 🎯 Mục tiêu
Khảo sát nhu cầu tra cứu thông tin da liễu bằng tiếng Việt, xác định mục tiêu, đối tượng sử dụng và phạm vi ranh giới hệ thống (hỗ trợ tra cứu tham khảo, không thay thế chẩn đoán y khoa).

### 📋 Các đầu việc cần làm
- [x] Khảo sát nghiệp vụ tra cứu bệnh học và cấu trúc phân loại ICD-11 WHO
- [x] Xác định các phân hệ chính: Thư viện, Triệu chứng, Ảnh, Hỏi đáp, Tài khoản, Quản trị
- [x] Viết tài liệu đặc tả yêu cầu chức năng (FR) và phi chức năng (NFR)
- [x] Soạn thảo tuyên bố miễn trừ trách nhiệm y tế (Medical Disclaimer)

### 🛠️ Kỹ thuật & Tệp liên quan
- **Phụ trách:** Tài liệu & Nghiệp vụ hệ thống
- **Tệp liên quan:** `README.md`, thư mục `docs/`

### ✅ Tiêu chí hoàn thành (DoD)
- [x] Đặc tả phạm vi, tác nhân và 12 Use Case có trong `docs/requirements.md`; chờ rà soát nghiệp vụ với người hướng dẫn
- [x] Xác định nguồn dữ liệu tham chiếu chuẩn hóa: ICD-11 của WHO và DermNet


=============================================================================
ISSUE #2
Title: [DATABASE] Thiết kế mô hình dữ liệu quan hệ tổng thể (ERD 13 bảng)
Milestone: Sprint 1
Labels: type:task, area:database, priority:high
-----------------------------------------------------------------------------
### 🎯 Mục tiêu
Thiết kế kiến trúc cơ sở dữ liệu quan hệ chuẩn hóa 3NF gồm 13 bảng đáp ứng toàn bộ các phân hệ của dự án Derma Library.

### 📋 Các đầu việc cần làm
- [x] Thiết kế nhóm bảng nội dung bệnh học: `tbldiseases`, `tblsymptoms`, `tbldisease_symptoms`
- [x] Thiết kế nhóm bảng tài liệu & phiên bản: `tblmedical_documents`, `tbldocument_versions`, `tblmedical_references`
- [x] Thiết kế nhóm bảng người dùng & phiên làm việc: `tblusers`, `tblsessions`, `tblbookmarks`, `tblsearch_history`
- [x] Thiết kế bảng kho ảnh (`tblimage_records`) và nhật ký kiểm toán (`tbladmin_audit_logs`)
- [x] Thiết lập ràng buộc toàn vẹn dữ liệu, khóa ngoại (FK) và Cascade Deletes

### 🛠️ Kỹ thuật & Tệp liên quan
- **Phụ trách:** Database Architect
- **Tệp liên quan:**
  - `docs/database/erd-tong-the.md`
  - `docs/database/erd-tong-the.mmd`
  - `docs/database/schema-sqlserver.sql`

### ✅ Tiêu chí hoàn thành (DoD)
- [x] Sơ đồ ERD 13 bảng hoàn chỉnh, không có bảng mồ côi
- [x] Xác định rõ kiểu dữ liệu tương thích cả SQL Server (NVARCHAR, BIT) và PostgreSQL


=============================================================================
ISSUE #3
Title: [DESIGN] Thiết kế Wireframe & Hệ thống giao diện (Design System)
Milestone: Sprint 1
Labels: type:task, area:frontend, priority:medium
-----------------------------------------------------------------------------
### 🎯 Mục tiêu
Xây dựng phong cách nhận diện giao diện định hướng y sinh học thực vật (botanical theme), typography tiếng Việt chuẩn font Be Vietnam Pro và bộ icon y tế trực quan.

### 📋 Các đầu việc cần làm
- [x] Thiết kế bảng màu y sinh học: xanh lá đậm, xanh ngọc, nền ngà dịu mắt
- [x] Cấu hình Typography tiếng Việt chuẩn với font Be Vietnam Pro
- [x] Xây dựng bộ CSS Design Tokens cơ sở
- [ ] Kiểm tra bố cục desktop/mobile theo `docs/interface-layout.md`

### 🛠️ Kỹ thuật & Tệp liên quan
- **Phụ trách:** Frontend / UI-UX
- **Tệp liên quan:**
  - `frontend/src/shared/styles/botanical.css`
  - `frontend/src/shared/styles/refinement.css`
  - `frontend/src/shared/styles/site.css`
  - `frontend/src/shared/components/Decor.tsx`

### ✅ Tiêu chí hoàn thành (DoD)
- [x] Giao diện đồng bộ phong cách, typography hiển thị sắc nét không lỗi font tiếng Việt
- [x] Bộ CSS tái sử dụng được cho tất cả các trang của hệ thống


=============================================================================
ISSUE #4
Title: [DEVOPS] Khởi tạo cấu trúc repository & cấu hình môi trường phát triển
Milestone: Sprint 1
Labels: type:devops, priority:high
-----------------------------------------------------------------------------
### 🎯 Mục tiêu
Khởi tạo cấu trúc monorepo phân tách rõ ràng giữa backend, frontend, mô hình nghiên cứu AI và bộ công cụ tiện ích.

### 📋 Các đầu việc cần làm
- [x] Thiết lập cấu trúc thư mục monorepo: `backend/`, `frontend/`, `research/`, `scripts/`, `docs/`
- [x] Cấu hình môi trường backend: FastAPI, Uvicorn, SQLAlchemy, `.venv`
- [x] Cấu hình môi trường frontend: React 19, TypeScript, Vite
- [x] Viết kịch bản tự động hóa khởi chạy dự án một chạm (`start.cmd`)

### 🛠️ Kỹ thuật & Tệp liên quan
- **Phụ trách:** DevOps / Fullstack
- **Tệp liên quan:**
  - `start.cmd`, `scripts/start.cmd`
  - `backend/requirements/base.txt`
  - `frontend/package.json`, `frontend/vite.config.ts`
  - `.gitignore`, `.dockerignore`

### ✅ Tiêu chí hoàn thành (DoD)
- [ ] Chạy lệnh `.\start.cmd` tự động cài đặt môi trường sạch và khởi chạy website tại `http://127.0.0.1:8000`
- [x] Endpoint kiểm tra sức khỏe hệ thống `/api/v1/health` phản hồi mã 200 OK


=============================================================================
ISSUE #5
Title: [DATABASE] Khởi tạo Database Schema, ORM Models & Migrations
Milestone: Sprint 2
Labels: type:feature, area:backend, area:database, priority:high
-----------------------------------------------------------------------------
### 🎯 Mục tiêu
Cài đặt 13 lớp Declarative Models trong SQLAlchemy ORM và xây dựng cơ chế migration tự động trên Microsoft SQL Server/PostgreSQL.

### 📋 Các đầu việc cần làm
- [x] Khai báo 13 Declarative Models trong `models.py`
- [x] Cấu hình engine kết nối đa CSDL (SQL Server via pyodbc, PostgreSQL via psycopg, SQLite)
- [x] Viết logic migration tự động sao lưu dữ liệu sang `storage/backups` trước khi migrate
- [x] Tự động tạo chỉ mục Index trên cột `name` của bảng `tbldiseases`

### 🛠️ Kỹ thuật & Tệp liên quan
- **Phụ trách:** Backend & Database (SQLAlchemy 2.0)
- **Tệp liên quan:**
  - `backend/app/database/models.py`
  - `backend/app/database/connection.py`
  - `backend/app/database/migrations/numeric_ids.py`
  - `backend/app/database/migrations/disease_name_index.py`

### ✅ Tiêu chí hoàn thành (DoD)
- [x] Backend tự động khởi tạo đủ 13 bảng khi chạy lệnh khởi động
- [x] Migration nâng cấp ID số và tạo index chạy trơn tru không gây lỗi schema


=============================================================================
ISSUE #6
Title: [DATA] Xây dựng công cụ import, chuẩn hóa & dịch dữ liệu ICD-11 WHO
Milestone: Sprint 2
Labels: type:task, area:backend, area:database, priority:high
-----------------------------------------------------------------------------
### 🎯 Mục tiêu
Xây dựng pipeline nhập liệu, chuẩn hóa thuật ngữ và dịch tiêu đề phân loại quốc tế ICD-11 từ WHO sang tiếng Việt kèm dữ liệu DermNet.

### 📋 Các đầu việc cần làm
- [x] Xây dựng script seed danh mục bệnh học cơ bản (`seed.py`)
- [x] Mở rộng tập bài viết bệnh da liễu từ nguồn DermNet và thư viện tổng quát
- [x] Dịch tiêu đề chương và tên bệnh ICD-11 sang tiếng Việt chuẩn hóa
- [x] Rà soát và loại bỏ các mục không phải bệnh (dược chất, thủ thuật phẫu thuật)

### 🛠️ Kỹ thuật & Tệp liên quan
- **Phụ trách:** Data Pipeline / Backend
- **Tệp liên quan:**
  - `backend/app/data/seed.py`
  - `backend/app/data/library_expansion.py`, `library_extended.py`, `library_dermnet.py`
  - `backend/app/modules/library/icd_chapters.py`
  - `backend/app/modules/library/icd_translation.py`

### ✅ Tiêu chí hoàn thành (DoD)
- [x] Seed thành công cơ sở dữ liệu với hàng trăm bài bệnh lý có cấu trúc hoàn chỉnh
- [x] Các bản ghi bệnh đều có liên kết đối chiếu mã ICD-11 của WHO


=============================================================================
ISSUE #7
Title: [BACKEND] Phát triển REST API cho Thư viện bệnh lý (/api/v1/diseases)
Milestone: Sprint 2
Labels: type:feature, area:backend, priority:high
-----------------------------------------------------------------------------
### 🎯 Mục tiêu
Xây dựng hệ thống REST API tra cứu danh mục bệnh học phục vụ tìm kiếm, lọc theo chuyên khoa, phân trang và truy xuất chi tiết bài viết.

### 📋 Các đầu việc cần làm
- [x] Xây dựng endpoint lấy danh sách bệnh có phân trang: `GET /api/v1/diseases`
- [x] Xây dựng endpoint lấy chi tiết bài viết theo slug: `GET /api/v1/diseases/{slug}`
- [x] Xây dựng thuật toán tìm kiếm không phân biệt dấu tiếng Việt (`normalize`)
- [x] Hỗ trợ lọc theo chuyên khoa (`specialty`) và nhóm chủ đề (`category`)

### 🛠️ Kỹ thuật & Tệp liên quan
- **Phụ trách:** Backend API (FastAPI)
- **Tệp liên quan:**
  - `backend/app/modules/library/routes.py`
  - `backend/app/modules/library/catalog.py`
  - `backend/app/modules/library/library_pagination.py`
  - `backend/app/modules/library/specialties.py`

### ✅ Tiêu chí hoàn thành (DoD)
- [ ] API tìm kiếm bệnh lý phản hồi dưới 200ms
- [x] Dữ liệu trả về đầy đủ: tóm tắt, tổng quan, yếu tố nguy cơ, phòng ngừa và tài liệu tham khảo nguồn


=============================================================================
ISSUE #8
Title: [FRONTEND] Xây dựng giao diện Thư viện bệnh lý (LibraryPage.tsx)
Milestone: Sprint 2
Labels: type:feature, area:frontend, priority:high
-----------------------------------------------------------------------------
### 🎯 Mục tiêu
Phát triển giao diện Thư viện bệnh lý thân thiện, hỗ trợ tìm kiếm nhanh, lọc theo chủ đề và xem chi tiết nội dung bệnh lý.

### 📋 Các đầu việc cần làm
- [x] Phát triển thanh tìm kiếm có xử lý Debounce chống nghẽn API
- [x] Thiết kế thẻ hiển thị tóm tắt bệnh (`DiseaseCard.tsx`)
- [x] Xây dựng danh mục chuyên khoa và chủ đề lọc (`TopicCard.tsx`, `ICDCatalog.tsx`)
- [x] Thiết kế Modal xem chi tiết bài viết, cấu trúc hình minh họa da (`SkinIllustration.tsx`) và tài liệu nguồn (`DocumentSources.tsx`)

### 🛠️ Kỹ thuật & Tệp liên quan
- **Phụ trách:** Frontend (React 19 + TypeScript)
- **Tệp liên quan:**
  - `frontend/src/features/library/LibraryPage.tsx`
  - `frontend/src/features/library/components/DiseaseCard.tsx`
  - `frontend/src/features/library/components/TopicCard.tsx`
  - `frontend/src/features/library/components/DocumentSources.tsx`

### ✅ Tiêu chí hoàn thành (DoD)
- [x] Giao diện hiển thị sắc nét, responsive trên cả điện thoại và máy tính
- [x] Xem chi tiết bài viết mượt mà, phân trang chuyển trang không giật lag


=============================================================================
ISSUE #9
Title: [FEATURE] Phát triển tính năng tra cứu theo đa triệu chứng (SymptomPage.tsx)
Milestone: Sprint 3
Labels: type:feature, area:frontend, area:backend, priority:high
-----------------------------------------------------------------------------
### 🎯 Mục tiêu
Xây dựng tính năng cho phép người dùng tick chọn nhiều triệu chứng lâm sàng để hệ thống tìm kiếm và xếp hạng các bệnh lý có khả năng liên quan nhất.

### 📋 Các đầu việc cần làm
- [x] Thiết kế bảng liên kết nhiều-nhiều `tbldisease_symptoms`
- [x] Xây dựng API lấy danh sách triệu chứng và API khớp triệu chứng: `GET /api/v1/symptoms`
- [x] Phát triển thuật toán xếp hạng bệnh theo số lượng triệu chứng trùng khớp
- [x] Xây dựng giao diện chọn triệu chứng trực quan trên `SymptomPage.tsx`

### 🛠️ Kỹ thuật & Tệp liên quan
- **Phụ trách:** Fullstack (FastAPI + React 19)
- **Tệp liên quan:**
  - `backend/app/modules/symptoms/routes.py`
  - `frontend/src/features/symptoms/SymptomPage.tsx`

### ✅ Tiêu chí hoàn thành (DoD)
- [x] Người dùng có thể chọn đồng thời nhiều triệu chứng để lọc bệnh liên quan
- [x] Hiển thị rõ tỷ lệ trùng khớp kèm khuyến cáo y tế tham khảo


=============================================================================
ISSUE #10
Title: [AUTH] Xây dựng hệ thống Xác thực, Phân quyền & Quản lý Session
Milestone: Sprint 3
Labels: type:feature, area:backend, area:frontend, priority:high
-----------------------------------------------------------------------------
### 🎯 Mục tiêu
Xây dựng hệ thống đăng ký, đăng nhập an toàn, bảo vệ phiên làm việc bằng Session token, CSRF token và phân quyền người dùng (User vs Admin).

### 📋 Các đầu việc cần làm
- [x] Cài đặt module băm mật khẩu Salt an toàn và kiểm tra độ mạnh mật khẩu
- [x] Xây dựng bảng quản lý phiên `tblsessions`, thiết lập cookie HttpOnly an toàn
- [x] Triển khai xác thực CSRF Token chống tấn công giả mạo yêu cầu
- [x] Xây dựng API và Modal đăng nhập/đăng ký trên giao diện người dùng

### 🛠️ Kỹ thuật & Tệp liên quan
- **Phụ trách:** Security / Fullstack
- **Tệp liên quan:**
  - `backend/app/core/security.py`, `password_policy.py`
  - `backend/app/modules/auth/routes.py`, `dependencies.py`
  - `frontend/src/features/auth/components/AuthModal.tsx`

### ✅ Tiêu chí hoàn thành (DoD)
- [x] Đăng nhập/đăng xuất hoạt động ổn định, bảo vệ route bằng cơ chế phân quyền RBAC
- [x] Mật khẩu người dùng được băm an toàn, không lưu văn bản thuần


=============================================================================
ISSUE #11
Title: [FEATURE] Cá nhân hóa người dùng: Bài viết đã lưu & Lịch sử tra cứu
Milestone: Sprint 3
Labels: type:feature, area:frontend, area:backend, priority:medium
-----------------------------------------------------------------------------
### 🎯 Mục tiêu
Xây dựng các tiện ích cá nhân hóa: lưu bài viết quan tâm (Bookmark) và tự động ghi nhận lịch sử tìm kiếm giúp người dùng dễ dàng xem lại.

### 📋 Các đầu việc cần làm
- [x] Xây dựng bảng lưu bài `tblbookmarks` và API lưu/hủy bài: `/api/v1/bookmarks`
- [x] Xây dựng bảng lịch sử `tblsearch_history` và API truy xuất/xóa lịch sử: `/api/v1/history`
- [x] Phát triển nút lưu nhanh (`SaveButton.tsx`) trên thẻ bài viết
- [x] Xây dựng màn hình Trang cá nhân (`ProfilePage.tsx`) và Lịch sử (`HistoryPage.tsx`)

### 🛠️ Kỹ thuật & Tệp liên quan
- **Phụ trách:** Fullstack (FastAPI + React 19)
- **Tệp liên quan:**
  - `backend/app/modules/profile/routes.py`
  - `backend/app/modules/history/routes.py`
  - `frontend/src/features/profile/ProfilePage.tsx`, `components/SaveButton.tsx`
  - `frontend/src/features/history/HistoryPage.tsx`

### ✅ Tiêu chí hoàn thành (DoD)
- [x] Người dùng bấm lưu bài viết được đồng bộ ngay lập tức vào cơ sở dữ liệu
- [x] Người dùng có toàn quyền xem và xóa nhật ký tìm kiếm cá nhân


=============================================================================
ISSUE #12
Title: [ADMIN] Xây dựng Bảng quản trị (CMS) & Quản lý phiên bản tài liệu
Milestone: Sprint 3
Labels: type:feature, area:frontend, area:backend, priority:high
-----------------------------------------------------------------------------
### 🎯 Mục tiêu
Xây dựng phân hệ quản trị viên cho phép quản lý tài khoản người dùng, biên tập và xuất bản bài viết bệnh lý kèm quản lý phiên bản tài liệu y khoa.

### 📋 Các đầu việc cần làm
- [x] Xây dựng công cụ CLI tạo tài khoản quản trị viên tối cao: `admin.py`
- [x] Xây dựng API quản lý tài khoản, xuất bản bài viết và lưu vết kiểm toán (`tbladmin_audit_logs`)
- [x] Thiết kế cơ chế quản lý lịch sử sửa đổi tài liệu qua bảng `tbldocument_versions` kèm băm SHA-256
- [x] Xây dựng Dashboard quản trị viên (`AdminPage.tsx`), `AccountManager.tsx`, `DocumentManager.tsx`

### 🛠️ Kỹ thuật & Tệp liên quan
- **Phụ trách:** Fullstack / Admin Management
- **Tệp liên quan:**
  - `backend/app/admin.py`
  - `backend/app/modules/admin/routes.py`
  - `frontend/src/features/admin/AdminPage.tsx`
  - `frontend/src/features/admin/components/AccountManager.tsx`, `DocumentManager.tsx`

### ✅ Tiêu chí hoàn thành (DoD)
- [x] Chỉ người dùng có role admin mới truy cập được các route quản trị
- [x] Thao tác sửa bài lưu snapshot nội dung mới và nhật ký; không tái tạo phiên bản lịch sử trước khi cơ chế này được bổ sung


=============================================================================
ISSUE #13
Title: [RESEARCH] Thu thập, làm sạch & chia tập dữ liệu ảnh bệnh lý
Milestone: Sprint 3
Labels: type:research, area:ai-ml, priority:high
-----------------------------------------------------------------------------
### 🎯 Mục tiêu
Thu thập tập dữ liệu ảnh da liễu; xây dựng công cụ tiền xử lý, gán nhãn, lọc trùng lặp và phân chia tập dữ liệu phục vụ huấn luyện mô hình ResNet-18.

### 📋 Các đầu việc cần làm
- [x] Xây dựng tệp ánh xạ danh mục nhãn thư mục bệnh (`folder-label-map.json`)
- [x] Viết script kiểm tra tính hợp lệ của ảnh (kích thước tối thiểu, định dạng hợp lệ qua Pillow)
- [x] Lọc bỏ ảnh trùng lặp bằng SHA-256 của byte file trong script nghiên cứu; hash pixel dùng riêng cho ảnh lưu trên web
- [x] Chia Train / Val / Test và loại ảnh trùng byte; chồng lặp bệnh nhân và ảnh gần trùng cần kiểm tra riêng

### 🛠️ Kỹ thuật & Tệp liên quan
- **Phụ trách:** AI / Data Researcher
- **Tệp liên quan:**
  - `research/prepare_folders.py`
  - `research/prepare_split.py`
  - `research/folder-label-map.json`

### ✅ Tiêu chí hoàn thành (DoD)
- [ ] Xác nhận tách biệt bệnh nhân khi có patient_id; dữ liệu thư mục hiện không có thông tin này
- [x] Xuất được file manifest mô tả chi tiết phân bố dữ liệu ảnh của từng lớp bệnh
