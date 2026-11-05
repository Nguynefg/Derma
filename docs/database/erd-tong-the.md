# ERD tổng thể website Derma

Một sơ đồ duy nhất gồm toàn bộ 13 bảng, gộp phần tài khoản, ảnh và nội dung thư viện. Mỗi bảng chỉ xuất hiện một lần.

Đối chiếu với `backend/app/database/models.py` ngày 23/10/2026. Chưa đối chiếu schema trực tiếp trên SQL Server. Kiểu dữ liệu trong hình là kiểu model SQLAlchemy; SQL Server có thể dùng kiểu tương ứng như NVARCHAR và BIT.

## Sơ đồ

```mermaid
erDiagram
    direction LR
    tbldiseases {
        integer disease_id PK
        varchar slug UK
        varchar name
        varchar english_name
        varchar category
        text summary
        text details
        text risk_factors
        text prevention
        json aliases
        boolean published
        varchar review_status
        integer version
        datetime updated_at
    }
    tbllibrary_updates {
        varchar update_id PK
        datetime applied_at
    }
    tblsymptoms {
        integer symptom_id PK
        varchar slug UK
        varchar name
    }
    tblusers {
        integer user_id PK
        varchar legacy_id UK
        varchar email UK
        varchar name
        text password_hash
        varchar role
        datetime created_at
    }
    tbladmin_audit_logs {
        integer audit_id PK
        varchar legacy_id UK
        integer actor_id FK
        varchar action
        varchar entity_id
        json snapshot
        datetime created_at
    }
    tblbookmarks {
        integer user_id PK,FK
        integer disease_id PK,FK
        datetime created_at
    }
    tbldisease_symptoms {
        integer disease_id PK,FK
        integer symptom_id PK,FK
    }
    tblimage_records {
        integer image_id PK
        varchar file_uuid UK
        integer user_id FK
        integer disease_id FK "NULL"
        varchar pixel_sha256
        varchar image_type
        integer width
        integer height
        boolean is_reference
        varchar consent_version
        datetime created_at
    }
    tblmedical_documents {
        integer document_id PK
        varchar slug UK
        integer disease_id FK
        varchar title
        varchar publisher
        text source_url
        text usage_note
        boolean published
        integer version
        datetime updated_at
    }
    tblmedical_references {
        integer reference_id PK
        varchar slug UK
        integer disease_id FK
        varchar title
        varchar publisher
        text url
        varchar accessed_at
        text usage_note
    }
    tblsearch_history {
        integer history_id PK
        varchar legacy_id UK
        integer user_id FK
        varchar mode
        varchar query
        json results
        varchar consent_version
        datetime created_at
    }
    tblsessions {
        varchar token_hash PK
        integer user_id FK
        varchar csrf
        datetime expires_at
    }
    tbldocument_versions {
        integer document_version_id PK
        varchar legacy_id UK
        integer document_id FK
        integer version
        varchar title
        varchar publisher
        text source_url
        text usage_note
        text content
        varchar checksum
        integer editor_id FK "NULL"
        datetime created_at
    }
    tblusers ||--o{ tbladmin_audit_logs : "actor_id"
    tblusers ||--o{ tblbookmarks : "user_id"
    tbldiseases ||--o{ tblbookmarks : "disease_id"
    tbldiseases ||--o{ tbldisease_symptoms : "disease_id"
    tblsymptoms ||--o{ tbldisease_symptoms : "symptom_id"
    tblusers ||--o{ tblimage_records : "user_id"
    tbldiseases |o--o{ tblimage_records : "disease_id"
    tbldiseases ||--o{ tblmedical_documents : "disease_id"
    tbldiseases ||--o{ tblmedical_references : "disease_id"
    tblusers ||--o{ tblsearch_history : "user_id"
    tblusers ||--o{ tblsessions : "user_id"
    tblmedical_documents ||--o{ tbldocument_versions : "document_id"
    tblusers |o--o{ tbldocument_versions : "editor_id"
```

## Chú thích

- PK: khóa chính; FK: khóa ngoại; UK: giá trị duy nhất.
- Hai cột PK trong `tblbookmarks` và `tbldisease_symptoms` tạo khóa chính ghép.
- `||`: đúng một; `o|` hoặc `|o`: không hoặc một; `o{`: không hoặc nhiều.
- `tblimage_records.disease_id` và `tbldocument_versions.editor_id` được phép NULL.
- Nhãn trên đường nối là cột khóa ngoại ở bảng con.
- `tbllibrary_updates` đứng độc lập vì model không khai báo khóa ngoại.
- `tbladmin_audit_logs.entity_id` là mã đối tượng được ghi nhật ký, không phải khóa ngoại cố định.
- `tblsearch_history.results` lưu JSON; không vẽ thêm quan hệ khóa ngoại từ các mã trong JSON.

Các ràng buộc xóa, index và giá trị mặc định xem trong model; sơ đồ không thay thế migration hoặc bản thiết kế vật lý SQL Server.
