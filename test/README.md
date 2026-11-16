# Hệ Thống Kiểm Thử Toàn Diện (AuthShield-LMS Test Suite)

Thư mục tập trung toàn bộ các kịch bản và công cụ kiểm thử chất lượng phần mềm và an toàn thông tin:

## Cấu trúc các bộ kiểm thử:
1. `e2e/`: Kiểm thử đầu cuối chu trình người dùng (Playwright / Cypress) - kiểm thử luồng đăng nhập SSO, chuyển đổi Workspace Switcher, nộp bài tập và Maker-Checker sửa điểm.
2. `integration/`: Kiểm thử tích hợp giữa API Gateway, Authenticator Service và School Service.
3. `security/`: Kịch bản kiểm tra an ninh mạng theo chuẩn TCVN 11930:2017 Cấp độ 3 (Anti-IDOR, Token Tampering, SoD Separation of Duties).
4. `performance/`: Kịch bản kiểm thử tải và kiểm tra giới hạn chịu tải (k6 / Apache JMeter).
5. `postman/`: Bộ sưu tập Postman Collection và Environment Variables phục vụ gọi API tự động qua Newman.
