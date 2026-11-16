# Cơ Sở Dữ Liệu & Quản Trị Di Trú (Database & Migrations)

Quản lý lược đồ CSDL và phiên bản hóa cấu trúc dữ liệu:
- `auth_db`: Quản lý 19 bảng định danh, người dùng, vai trò, mfa_credentials, audit_logs.
- `school_db`: Quản lý học vụ, lớp học, môn học, phân công giảng dạy, điểm số, bài tập, học phí.
- `audit_db`: Kho lưu trữ nhật ký kiểm toán bất biến chuỗi băm (Chained HMAC-SHA256).
- `migrations/`: Chứa các tệp script SQL định phiên bản (V1, V2, ...) phục vụ Flyway / Liquibase.
