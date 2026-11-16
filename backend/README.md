# Phân Hệ Backend & Dịch Vụ Bảo Mật (AuthShield-LMS)

Thư mục này chứa toàn bộ các dịch vụ backend cốt lõi của hệ thống theo kiến trúc Decoupled Gatekeeper (Zero Trust) và quy chuẩn TCVN 11930:2017 Cấp độ 3:

## Cấu trúc các phân hệ:
1. `api-gateway/`: Chốt chặn biên (PEP - Policy Enforcement Point) kiểm soát JWT, rate limiting, anti-IDOR.
2. `authenticator-service/`: Cổng xác thực tập trung & quyết định chính sách (IdP & PDP), quản lý MFA đa cấp (S1, S2, S3) và cấp phát Token ngữ cảnh Workspace Switcher.
3. `school-service/`: Tầng nghiệp vụ quản lý đào tạo trường học (Spring Boot), quản lý điểm số, phân công chuyên môn, chữ ký số S3 và quy trình Maker-Checker sửa điểm.
4. `database/`: Quản lý lược đồ CSDL (auth_db, school_db, audit_db) và script di trú dữ liệu (Flyway / Liquibase).
5. `docker/`: Docker Compose và cấu hình môi trường chạy cục bộ (PostgreSQL, Redis Cluster, MinIO S3).
