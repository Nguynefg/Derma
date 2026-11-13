# Derma Library

Website hỗ trợ tra cứu thông tin bệnh lý bằng tiếng Việt theo tên và triệu chứng. Dự án phát triển thêm chức năng phân loại ảnh da liễu bằng mô hình chạy cục bộ và hỏi đáp dựa trên tài liệu trong thư viện.

## Chức năng chính

| Chức năng | Mô tả |
|---|---|
| **Thư viện bệnh lý** | Tìm kiếm theo tên tiếng Việt, tên tiếng Anh hoặc từ khóa; lọc theo chuyên khoa, nhóm chủ đề và dấu hiệu; phân trang và sắp xếp kết quả. |
| **Chi tiết bệnh lý** | Hiển thị tóm tắt, tổng quan, yếu tố liên quan, thông tin chăm sóc và tài liệu nguồn tùy theo dữ liệu của từng bài. |
| **Tra cứu triệu chứng** | Cho phép chọn một hoặc nhiều dấu hiệu để tìm các bài bệnh lý có liên quan trong cơ sở dữ liệu. |
| **Tài khoản cá nhân** | Đăng nhập, quản lý hồ sơ, lưu bài viết, xem lịch sử tra cứu và quản lý ảnh riêng. |
| **Quản trị** | Biên tập và xuất bản bài viết, quản lý tài liệu và phiên bản, tài khoản, nhãn ảnh và nhật ký thao tác. |

## Phân loại ảnh da liễu và hỏi đáp tài liệu

### Phân loại ảnh bằng ResNet-18

Dự án đã có mã nguồn chuẩn bị dữ liệu, huấn luyện, đánh giá và đóng gói mô hình ResNet-18 bằng PyTorch và Torchvision. Backend có nhánh hỗ trợ nạp mô hình và chạy suy luận trên máy chủ.

Luồng mặc định trên giao diện: người dùng tải ảnh và chọn vùng cần xem → backend kiểm tra và tiền xử lý ảnh → ResNet-18 phân loại nhóm ảnh → hệ thống đối chiếu nhãn với bài viết trong SQL Server. Khi chưa đủ cơ sở, hệ thống cần trả trạng thái **Chưa xác định**.

Mô hình phân loại theo **nhóm**. Giao diện gửi ảnh tới nhánh cục bộ. Cần cài model card và trọng số hợp lệ; nếu chưa có, hệ thống trả chưa xác định. Ngưỡng điểm không bảo đảm nhận ra mọi ảnh ngoài tập huấn luyện.

### Hỏi đáp dựa trên tài liệu

Chức năng hỏi đáp được thiết kế để nhận câu hỏi, tìm nội dung liên quan trong tài liệu đã xuất bản và hiển thị đoạn trích kèm nguồn. Khi thư viện không có tài liệu phù hợp, hệ thống thông báo chưa tìm thấy thông tin.

Giao diện hội thoại dùng API nội bộ `/api/v1/chat`, truy xuất BM25 và trả đoạn trích nguyên văn kèm nguồn; không cần Gemini API key. Đây là hỏi đáp trích xuất, không phải mô hình ngôn ngữ trò chuyện tự do. Có nhánh Gemini/Google Search dự phòng khi thư viện chưa có bài hoặc tài liệu phù hợp và người dùng cho phép. Nguồn web được hiển thị riêng; xem [luồng kết hợp](docs/hybrid-ai.md).

## Dữ liệu và nguồn tham khảo

Dữ liệu phân loại ban đầu được nhập từ ICD-11 của Tổ chức Y tế Thế giới (WHO), sau đó dịch, chuẩn hóa và tổ chức lại theo cấu trúc bài viết. Các bản ghi mẫu đã đối chiếu trong SQL Server có lưu liên kết đến [nền tảng ICD-11 của WHO](https://icd.who.int/dev11/l-m/en).

Dữ liệu phân loại cung cấp tên và thông tin phân nhóm. Mức độ đầy đủ của nội dung và tài liệu tham khảo phụ thuộc từng bài. Thông tin ghi công ảnh thư viện được tập hợp tại trang **Nguồn**.

## Công nghệ sử dụng

| Thành phần | Công nghệ |
|---|---|
| Giao diện | React, TypeScript, Vite, CSS |
| Backend và máy chủ web | Python, FastAPI, Uvicorn |
| Cơ sở dữ liệu | Microsoft SQL Server |
| Kết nối và truy vấn dữ liệu | SQLAlchemy, pyodbc |
| Kiểm tra và tiền xử lý ảnh | Pillow |
| Huấn luyện và chạy mô hình ảnh | PyTorch, Torchvision, ResNet-18 |
| Kiểm thử backend | pytest |

## Kiến trúc hệ thống

Giao diện React gửi yêu cầu đến FastAPI. Backend sử dụng SQL Server để tra cứu bệnh lý, triệu chứng, tài liệu và quản lý tài khoản. Nhánh phân loại ảnh chạy ResNet-18 trên máy chủ và dùng dữ liệu thư viện để liên kết nhãn với bài viết phù hợp.

## Cấu trúc dự án

| Đường dẫn | Nội dung |
|---|---|
| `frontend/src/` | Mã nguồn giao diện và các trang theo chức năng |
| `backend/app/` | API, nghiệp vụ, xác thực và truy cập cơ sở dữ liệu |
| `backend/models/` | Vị trí lưu mô hình ảnh đã đóng gói |
| `backend/requirements/` | Danh sách thư viện Python |
| `backend/tests/` | Kiểm thử tự động |
| `research/` | Chuẩn bị dữ liệu, huấn luyện và đánh giá mô hình |
| `scripts/` | Công cụ khởi động và xử lý dữ liệu |
| `docs/` | Tài liệu kiến trúc, cơ sở dữ liệu và sơ đồ |

## Chạy trên Windows

1. Cài Python **3.11 trở lên**, Node.js **22 trở lên**, Microsoft SQL Server và driver ODBC phù hợp.
2. Thiết lập kết nối SQL Server bằng `backend/database.local.json` hoặc biến môi trường theo cấu hình của backend.
3. Nếu thử nghiệm nhánh phân loại ảnh cục bộ, chuẩn bị bộ trọng số, tệp cấu hình mô hình và các thư viện PyTorch, Torchvision.
4. Mở PowerShell tại thư mục gốc dự án và chạy:

```powershell
.\start.cmd
```

Truy cập [http://127.0.0.1:8000](http://127.0.0.1:8000). Giữ terminal mở khi sử dụng website; nhấn `Ctrl + C` để dừng máy chủ.

Thông tin đăng nhập cơ sở dữ liệu, ảnh riêng, dữ liệu huấn luyện và trọng số không có trong repository cần được quản lý riêng.

## Kế hoạch thực hiện

| Sprint | Nội dung |
|---|---|
| **Sprint 1** | Khảo sát, phân tích yêu cầu và thiết kế hệ thống |
| **Sprint 2** | Xây dựng cơ sở dữ liệu và thư viện bệnh lý |
| **Sprint 3** | Phát triển tra cứu triệu chứng, tài khoản và quản trị |
| **Sprint 4** | Huấn luyện mô hình phân loại ảnh và xây dựng hỏi đáp tài liệu |
| **Sprint 5** | Kiểm thử, tối ưu và hoàn thiện sản phẩm |

## Phạm vi sử dụng

Derma phục vụ tra cứu thông tin sức khỏe. Kết quả tìm kiếm theo triệu chứng, đoạn trích tài liệu và nhóm ảnh do mô hình gợi ý chỉ dùng để tham khảo, không thay thế việc khám và chẩn đoán của bác sĩ.

## Tài liệu yêu cầu và nghiệm thu

- [Yêu cầu và Use Case](docs/requirements.md)
- [Bố cục và tiêu chí kiểm tra giao diện](docs/interface-layout.md)
- [Kế hoạch 5 Sprint](docs/ISSUES.md)

Các snapshot phiên bản mới áp dụng cho thao tác biên tập từ bản cập nhật này; không tái tạo lịch sử chưa từng được lưu. Hiệu năng SQL Server và cấu hình bảo vệ nhánh GitHub cần xác nhận trên môi trường thật.
