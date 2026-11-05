# Derma Library

Website hỗ trợ tra cứu thông tin bệnh lý bằng tiếng Việt theo tên, triệu chứng và hình ảnh da liễu.

## Giới thiệu

Derma tập hợp thông tin bệnh lý trong một thư viện có tìm kiếm, phân nhóm và liên kết nguồn tham khảo. Người dùng có thể đọc thông tin bệnh, tra cứu theo triệu chứng, sử dụng trợ lý AI và tìm hiểu các chủ đề liên quan từ ảnh da liễu.

Hệ thống cung cấp công cụ quản trị để cập nhật bài viết, quản lý tài liệu, tài khoản và nhãn ảnh.

## Mục tiêu

- Tổ chức thông tin bệnh lý bằng tiếng Việt, kèm tên tiếng Anh để đối chiếu.
- Hỗ trợ tìm kiếm theo tên bệnh, từ khóa và triệu chứng.
- Hỗ trợ phân tích hình ảnh da liễu và hỏi đáp thông tin.
- Quản lý nội dung, tài liệu và lịch sử chỉnh sửa.
- Cung cấp giao diện sử dụng được trên máy tính và điện thoại.

## Đối tượng sử dụng

| Đối tượng | Chức năng |
|---|---|
| Khách truy cập | Tra cứu và sử dụng các chức năng công khai |
| Người dùng đăng nhập | Quản lý hồ sơ, bài đã lưu, lịch sử và ảnh riêng |
| Quản trị viên | Quản lý bài viết, tài liệu, tài khoản và nhãn ảnh |

## Chức năng chính

### Thư viện bệnh lý

- Tìm kiếm theo tên tiếng Việt, tiếng Anh hoặc từ khóa.
- Lọc theo chuyên khoa, nhóm chủ đề và dấu hiệu liên quan.
- Phân trang và sắp xếp theo tên hoặc thời điểm cập nhật.
- Xem tóm tắt, tổng quan, yếu tố liên quan và nội dung chăm sóc khi có dữ liệu.
- Mở tài liệu nguồn để đối chiếu.
- Hiển thị ảnh cho các mục có ảnh phù hợp; thông tin ghi công được tập hợp tại trang Nguồn.

Mức độ đầy đủ của nội dung phụ thuộc từng bài viết.

### Tra cứu triệu chứng

Người dùng chọn một hoặc nhiều dấu hiệu để tìm bài viết liên quan. Hệ thống đối chiếu dữ liệu giữa bệnh lý và triệu chứng trong CSDL.

Thứ tự kết quả không thể hiện xác suất mắc bệnh.

### Phân tích hình ảnh da liễu

- Tải ảnh và chọn vùng cần xem.
- Kiểm tra định dạng, dung lượng và kích thước ảnh.
- Xử lý ảnh trước khi phân tích.
- Hiển thị nhận xét và bài viết liên quan khi có đủ cơ sở.
- Quản lý ảnh riêng theo quyền truy cập.

Luồng giao diện đã được kiểm tra sử dụng Gemini API. Backend đồng thời có nhánh hỗ trợ mô hình ResNet-18 cục bộ.

### Trợ lý và hỏi đáp

- Hội thoại nhiều lượt qua Gemini API.
- Sử dụng nội dung thư viện làm ngữ cảnh khi phù hợp.
- Hiển thị bài viết và nguồn liên quan khi có.
- Giữ hội thoại trong phiên giao diện, không tự lưu thành lịch sử trò chuyện trong SQL Server.

### Tài khoản và quản trị

- Đăng nhập, đăng xuất và quản lý hồ sơ.
- Lưu và bỏ lưu bài viết.
- Xem lịch sử tra cứu.
- Biên tập bài viết, quản lý trạng thái xuất bản.
- Quản lý tài liệu và phiên bản.
- Quản lý tài khoản, duyệt nhãn ảnh và ghi nhật ký quản trị.

## Dữ liệu và nguồn tham khảo

Dữ liệu phân loại bệnh lý ban đầu được nhập từ ICD-11 của Tổ chức Y tế Thế giới (WHO), sau đó dịch, chuẩn hóa và chuyển sang cấu trúc bài viết.

Các bản ghi mẫu đã được đối chiếu trong SQL Server có lưu nguồn:

https://icd.who.int/dev11/l-m/en

Đây là nền tảng phát triển của WHO; khi trích dẫn trong báo cáo cần ghi rõ phiên bản hoặc thời điểm thu thập nếu xác định được.

Nội dung bổ sung được tổng hợp từ các tài liệu y khoa tham khảo. Dữ liệu phân loại không đồng nghĩa với bài viết đã được biên soạn đầy đủ hoặc thẩm định chuyên môn.

## Công nghệ sử dụng

| Thành phần | Công nghệ |
|---|---|
| Frontend | React, TypeScript, Vite, CSS |
| Backend | Python, FastAPI |
| Web server | Uvicorn |
| Cơ sở dữ liệu | Microsoft SQL Server |
| Truy cập CSDL | SQLAlchemy, pyodbc |
| Xử lý ảnh | Pillow |
| AI tích hợp | Gemini API |
| Nghiên cứu mô hình ảnh | PyTorch, Torchvision, ResNet-18 |
| Kiểm thử | pytest |

## Kiến trúc hoạt động

```text
Người dùng
    ↓
Giao diện React
    ↓
Backend FastAPI
    ├── SQL Server: tra cứu và quản lý dữ liệu
    ├── Gemini API: hội thoại và phân tích ảnh
    └── ResNet-18: nhánh xử lý ảnh cục bộ
    ↓
Hiển thị kết quả
```

Tìm kiếm thư viện và tra cứu triệu chứng sử dụng dữ liệu trong hệ thống; không phải mọi yêu cầu đều gọi AI.

## Nghiên cứu mô hình cục bộ

Dự án có công cụ chuẩn bị dữ liệu, huấn luyện, đánh giá và đóng gói ResNet-18 bằng phương pháp học chuyển giao.

Các thành phần gồm:

- Ánh xạ nhãn ảnh với nhóm bệnh.
- Chia tập huấn luyện, kiểm định và kiểm thử.
- Huấn luyện và lưu trọng số.
- Đánh giá precision, recall, F1 và ma trận nhầm lẫn.
- Kiểm tra và nạp bộ mô hình tại backend.

Kết quả mô hình phục vụ nghiên cứu, chưa phải công cụ chẩn đoán.

### Hướng phát triển tiếp theo

- Cải thiện dữ liệu và chất lượng mô hình ảnh.
- Chuyển luồng giao diện sang mô hình cục bộ sau khi đánh giá.
- Xây dựng hỏi đáp bằng tìm kiếm và trích đoạn tài liệu.
- Giảm phụ thuộc dịch vụ AI bên ngoài.
- Hoàn thiện xử lý trường hợp chưa xác định.

Các mục trên là kế hoạch phát triển, chưa được coi là đã hoàn thành toàn bộ.

## Cấu trúc dự án

```text
derma-library/
├── frontend/
│   └── src/
│       ├── app/            # Khởi tạo và điều hướng
│       ├── features/       # Giao diện theo chức năng
│       ├── pages/          # Trang chủ và nguồn tham khảo
│       └── shared/         # Thành phần, API, kiểu dữ liệu và CSS chung
├── backend/
│   ├── app/
│   │   ├── main.py         # Khởi tạo FastAPI
│   │   ├── core/           # Cấu hình, bảo mật và schema
│   │   ├── database/       # Kết nối, model và migration
│   │   ├── modules/        # API và nghiệp vụ
│   │   ├── integrations/   # Kết nối dịch vụ bên ngoài
│   │   └── data/           # Dữ liệu khởi tạo và từ điển
│   ├── models/             # Mô hình đã đóng gói
│   ├── requirements/       # Thư viện Python
│   └── tests/              # Kiểm thử tự động
├── research/               # Huấn luyện và đánh giá mô hình
├── scripts/                # Công cụ chạy và xử lý dữ liệu
├── docs/                   # Tài liệu hệ thống
├── storage/                # Sao lưu, dữ liệu nhập, xuất và file tạm
├── README.md
└── start.cmd
```

Một số dữ liệu, trọng số và cấu hình riêng có thể không được đưa lên GitHub. Cần chuẩn bị riêng khi cài đặt.

## Yêu cầu môi trường

- Python 3.11 trở lên.
- Node.js 22 trở lên và npm.
- Microsoft SQL Server.
- Driver ODBC phù hợp.
- CSDL đã được thiết lập.
- Khóa Gemini API nếu sử dụng chức năng tương ứng.
- Bộ trọng số và thư viện PyTorch nếu chạy mô hình cục bộ.

## Cấu hình

- Thiết lập kết nối SQL Server tại `backend/database.local.json` hoặc qua biến môi trường theo cơ chế của backend.
- Cấu hình khóa và tên model Gemini trong `.env` nếu sử dụng.
- Không đưa khóa API, mật khẩu, cấu hình kết nối riêng hoặc ảnh người dùng lên repository công khai.
- Sao lưu SQL Server riêng; GitHub không tự lưu dữ liệu CSDL.
- Kiểm tra phụ thuộc trước khi xóa dữ liệu trong `storage/`.

## Chạy trên Windows

Mở terminal tại thư mục gốc dự án.

### PowerShell

```powershell
.\start.cmd
```

### Command Prompt

```cmd
start.cmd
```

Lệnh khởi động chuẩn bị thư viện, build frontend và chạy Uvicorn.

Địa chỉ mặc định:

http://127.0.0.1:8000

Giữ terminal hoạt động khi sử dụng. Nhấn `Ctrl + C` để dừng máy chủ.

### Đổi cổng

```powershell
.\scripts\start.ps1 -Port 8080
```

Truy cập:

http://127.0.0.1:8080

## Phát triển và kiểm thử

### Frontend

```powershell
cd frontend
npm ci
npm run dev
```

Build bản triển khai:

```powershell
npm run build
```

### Backend

Cài công cụ kiểm thử từ thư mục gốc:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements\dev.txt
```

Chạy kiểm thử:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests
```

Một số kiểm thử cần cấu hình hoặc thư viện bổ sung. Nếu đã loại bỏ script cũ, cần cập nhật các kiểm thử còn phụ thuộc chúng.

## Kế hoạch phát triển

| Sprint | Nội dung |
|---|---|
| Sprint 1 | Khảo sát, phân tích yêu cầu và thiết kế hệ thống |
| Sprint 2 | Xây dựng CSDL và thư viện bệnh lý |
| Sprint 3 | Phát triển triệu chứng, tài khoản và quản trị |
| Sprint 4 | Huấn luyện mô hình ảnh và xây dựng hỏi đáp tài liệu |
| Sprint 5 | Kiểm thử, tối ưu và hoàn thiện sản phẩm |

## Phạm vi sử dụng

Derma hỗ trợ tra cứu và tìm hiểu sức khỏe, không thay thế việc khám và chẩn đoán của bác sĩ.

Kết quả tìm kiếm, gợi ý từ ảnh và phản hồi AI cần được đối chiếu với nguồn tham khảo. Chất lượng kết quả phụ thuộc dữ liệu, ảnh đầu vào, mô hình và cấu hình hệ thống.
