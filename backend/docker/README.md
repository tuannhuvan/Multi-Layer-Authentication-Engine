# Hạ Tầng Container Hóa Cục Bộ (Docker Environment)

Thư mục chứa các tệp Dockerfile và Docker Compose phục vụ khởi chạy hạ tầng phát triển:
- PostgreSQL (Cụm CSDL chính).
- Redis Cluster (Bộ nhớ đệm session, quản lý blacklist token JWT).
- MinIO (Kho lưu trữ tệp tin học liệu và bài nộp học sinh tương thích chuẩn AWS S3).
- MailHog / Mock SMS (Giả lập cổng thông báo OTP và email).
