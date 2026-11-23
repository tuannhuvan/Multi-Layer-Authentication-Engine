# ADR-001: Kiến trúc Modular Monolith / Gatekeeper Zero Trust & Quy trình AI-Agent V2.1

- **Trạng thái**: `APPROVED` (G2 Baseline `DESIGN-002`)
- **Người duyệt**: Ng Tuân (Tech Lead / Architect)

## 1. Quyết định kiến trúc
1. **Contract-First & ProblemDetail (RFC 9457)**: Mọi API giữa Frontend (`frontend/`), Mobile (`app/`) và Backend (`backend/`) đều định nghĩa tại `api/openapi.yaml` trước khi hiện thực (P2). Mọi lỗi trả về chuẩn `application/problem+json` có `traceId`.
2. **Xác thực Đa tầng (Multi-Layer Authentication ACR S1/S2/S3)**:
   - `S1`: Đăng nhập cơ bản (xem thông tin).
   - `S2`: OTP / MFA (nhập điểm thường kỳ, tạo đề xuất Maker).
   - `S3`: Chữ ký số / Step-up Hardware Token (Ban Giám hiệu duyệt sửa điểm sau khóa sổ - Checker).
3. **Contract Mocker cho P4 Song song**: FE Dev sử dụng `tools/mocker/contract_mocker.py` để sinh mock server và dữ liệu chuẩn từ `api/openapi.yaml` trong lúc BE Dev phát triển song song, sau đó chạy integration test trên cây tích hợp.
