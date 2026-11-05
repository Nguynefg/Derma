# Derma Library

Website thư viện sức khỏe đa chuyên khoa, tích hợp trợ lý AI và hỗ trợ phân tích hình ảnh da liễu.

## Thông tin đề tài

- **Tên đề tài:** Xây dựng website hỗ trợ tra cứu thông tin bệnh lý theo triệu chứng và hình ảnh da liễu, tích hợp trợ lý AI.
- **Người thực hiện:** Phan Hoàng Nguyên.
- **Hình thức:** Cá nhân, 1 thành viên.

## Giới thiệu

Derma giúp người dùng tìm hiểu bệnh lý bằng tiếng Việt, tra cứu theo tên hoặc triệu chứng, trò chuyện với trợ lý AI và tham khảo thông tin từ hình ảnh da liễu.

Website tập trung thông tin sức khỏe trong một hệ thống có tìm kiếm, phân nhóm và liên kết nguồn tham khảo. Quản trị viên có thể cập nhật bài viết, quản lý tài liệu, tài khoản và nhãn ảnh.

## Mục tiêu

- Xây dựng thư viện bệnh lý bằng tiếng Việt, kèm tên tiếng Anh để đối chiếu.
- Hỗ trợ tìm bài viết theo tên bệnh, từ khóa và triệu chứng.
- Tích hợp AI để giải thích thông tin và hỗ trợ phân tích ảnh da liễu.
- Cung cấp công cụ quản lý và cập nhật nội dung.
- Xây dựng giao diện dễ đọc, sử dụng được trên máy tính và điện thoại.

## Đối tượng sử dụng

| Đối tượng | Chức năng |
|---|---|
| Khách truy cập | Tra cứu thông tin và sử dụng các chức năng công khai |
| Người dùng đăng nhập | Quản lý hồ sơ, bài đã lưu, lịch sử và ảnh riêng theo chức năng được cung cấp |
| Quản trị viên | Quản lý bài viết, tài liệu, tài khoản và duyệt nhãn ảnh |

## Chức năng chính

### Thư viện bệnh lý

- Tìm kiếm theo tên tiếng Việt, tiếng Anh hoặc từ khóa.
- Lọc theo chuyên khoa, nhóm chủ đề và dấu hiệu liên quan.
- Phân trang, sắp xếp theo tên hoặc thời điểm cập nhật.
- Xem tóm tắt, tổng quan, yếu tố liên quan, nội dung chăm sóc và nguồn tham khảo khi có dữ liệu.
- Hiển thị ảnh tham khảo có thông tin nguồn và giấy phép.

Mức độ đầy đủ của nội dung phụ thuộc từng bài viết.

### Tra cứu triệu chứng

Người dùng chọn một hoặc nhiều dấu hiệu để tìm bài viết có liên quan. Hệ thống đối chiếu các liên kết giữa bệnh lý và triệu chứng trong CSDL. Thứ tự kết quả không phải xác suất mắc bệnh.

### Phân tích hình ảnh da liễu

Người dùng chọn ảnh và vùng cần xem để yêu cầu AI hỗ trợ phân tích. Kết quả có thể gồm nhận xét và các chủ đề tham khảo trong thư viện.

Ảnh riêng được quản lý theo quyền truy cập, không tự trở thành ảnh công khai. Phạm vi hiện tại tập trung vào ảnh da liễu.

### Trợ lý AI

- Hội thoại nhiều lượt bằng Gemini API.
- Giải thích thông tin và hỗ trợ câu hỏi tiếp nối.
- Truy xuất bài viết đã xuất bản để hỗ trợ trả lời khi phù hợp.
- Hiển thị nguồn tham khảo liên quan khi có.

Hội thoại được giữ trong phiên sử dụng của giao diện, không tự lưu thành lịch sử trò chuyện trong SQL Server.

### Tài khoản và quản trị

- Đăng nhập và quản lý hồ sơ.
- Lưu bài viết và xem lịch sử tra cứu.
- Quản lý ảnh riêng.
- Biên tập bài viết, tài liệu và phiên bản.
- Quản lý tài khoản, duyệt nhãn ảnh và ghi nhận nhật ký quản trị.

## Công nghệ sử dụng

| Thành phần | Công nghệ | Vai trò |
|---|---|---|
| Frontend | React, TypeScript, Vite, CSS | Xây dựng giao diện |
| Backend | Python, FastAPI | Xử lý API và nghiệp vụ |
| Web server | Uvicorn | Chạy ứng dụng FastAPI |
| CSDL | Microsoft SQL Server | Lưu dữ liệu của hệ thống |
| Truy cập CSDL | SQLAlchemy, pyodbc | Kết nối và truy vấn dữ liệu |
| AI tích hợp | Gemini API | Hội thoại và phân tích ảnh |
| Nghiên cứu mô hình ảnh | PyTorch, Torchvision, ResNet-18 | Huấn luyện và đánh giá phân loại ảnh |
| Công cụ | VS Code, SSMS, npm, `.venv`, pytest | Phát triển và kiểm thử |

Phần ResNet-18 là nghiên cứu phân loại nhóm ảnh, được đánh giá riêng với dịch vụ Gemini.

## Nguyên lý hoạt động

```text
Người dùng
    ↓
Giao diện React
    ↓
API FastAPI
    ├── SQL Server: tra cứu và quản lý dữ liệu
    └── Gemini API: hội thoại và phân tích ảnh
    ↓
Hiển thị kết quả trên website
```

Tìm kiếm thư viện và đối chiếu triệu chứng sử dụng dữ liệu của hệ thống; không phải mọi thao tác đều gọi AI.

## Cấu trúc dự án

```text
derma-library/
├── frontend/
│   └── src/
│       ├── app/           # Khởi tạo React và điều hướng
│       ├── features/      # Giao diện theo chức năng
│       ├── pages/         # Trang chủ, nguồn tham khảo
│       └── shared/        # Thành phần, API, kiểu dữ liệu và CSS chung
├── backend/
│   ├── app/
│   │   ├── main.py        # Khởi tạo FastAPI
│   │   ├── core/          # Cấu hình, bảo mật, schema
│   │   ├── database/      # Kết nối, model và migration
│   │   ├── modules/       # API và nghiệp vụ theo chức năng
│   │   ├── integrations/ # Kết nối dịch vụ bên ngoài
│   │   └── data/          # Dữ liệu khởi tạo và từ điển
│   ├── models/            # Mô hình ảnh đã đóng gói
│   ├── requirements/      # Danh sách thư viện Python
│   └── tests/             # Kiểm thử tự động
├── research/              # Huấn luyện và đánh giá mô hình
├── scripts/               # Công cụ chạy và xử lý dữ liệu
├── docs/                  # Tài liệu hệ thống
├── storage/               # Sao lưu, dữ liệu nhập, xuất và file tạm
├── .env                   # Cấu hình riêng trên máy
├── README.md
└── start.cmd              # Khởi động trên Windows
```

## Yêu cầu môi trường

- Python **3.11 trở lên**.
- Node.js **22 trở lên**, có npm.
- Microsoft SQL Server và CSDL đã được cấu hình.
- Driver ODBC phù hợp để kết nối SQL Server.
- Khóa Gemini API nếu sử dụng chức năng AI.

## Cấu hình

- Cấu hình SQL Server cục bộ tại `backend/database.local.json` hoặc qua biến môi trường theo cơ chế của backend.
- Thiết lập khóa API và các biến môi trường cần thiết trong `.env`.
- Không đưa mật khẩu hoặc khóa API thật vào mã nguồn công khai.
- Không xóa toàn bộ `storage/` khi chưa kiểm tra các công cụ còn phụ thuộc dữ liệu trong đó.

Ảnh và mô hình phục vụ backend nằm trong `backend/data` và `backend/models`. Ảnh công khai của thư viện nằm trong tài nguyên frontend.

## Chạy trên Windows

Mở terminal tại thư mục gốc dự án.

**PowerShell:**

```powershell
.\start.cmd
```

**Command Prompt — CMD:**

```cmd
start.cmd
```

Lệnh khởi động sẽ chuẩn bị thư viện cần thiết, build frontend rồi chạy Uvicorn.

Truy cập:

```text
http://127.0.0.1:8000
```

Giữ terminal hoạt động trong khi sử dụng website. Nhấn **Ctrl + C** để dừng máy chủ.

Cách chạy này không cần Docker.

### Đổi cổng bằng PowerShell

```powershell
.\scripts\start.ps1 -Port 8080
```

Sau đó truy cập:

```text
http://127.0.0.1:8080
```

## Lệnh dành cho phát triển

### Frontend

Chạy từ thư mục gốc:

```powershell
cd frontend
npm ci
npm run dev
```

Build bản triển khai:

```powershell
npm run build
```

### Kiểm thử backend

Cài công cụ kiểm thử từ thư mục gốc:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements\dev.txt
```

Chạy kiểm thử từ thư mục `backend`:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests
```

Một số kiểm thử cần công cụ hoặc cấu hình bổ sung tùy chức năng. Nếu đã loại bỏ các script xử lý dữ liệu cũ, các kiểm thử phụ thuộc chúng cũng cần được cập nhật.

## Phạm vi và giới hạn

Derma cung cấp thông tin tham khảo, không thay thế việc khám và chẩn đoán của bác sĩ. Kết quả tìm kiếm, nhãn mô hình và gợi ý từ ảnh không phải kết luận bệnh lý.

Chất lượng phản hồi AI phụ thuộc dữ liệu, cấu hình, kết nối và hạn mức dịch vụ. Nội dung quan trọng cần được đối chiếu với nguồn tham khảo.

---

**Người thực hiện: Phan Hoàng Nguyên**
