# Runbook Vận hành, Migration và Khôi phục (§15)

## 1. Nguyên tắc Release & Digest (§15.1)
- Build image **một lần duy nhất** tại stage `package` trên nhánh chính, xuất `image.json` kèm SHA-256 digest, SBOM và provenance.
- Triển khai cùng một digest qua `staging` → kiểm chứng `verify-staging` → chờ Release Owner duyệt G5 → `deploy-production`.

## 2. Chiến lược Migration & Rollback (§15.2)
- **Expand → Migrate → Switch → Contract**: Không sửa migration đã áp dụng; mọi thay đổi schema phải tương thích ngược với phiên bản ứng dụng liền trước.
- **Trạng thái migration không rõ sau lỗi**: Dừng ngay và đối chiếu bảng `flyway_schema_history`; tuyệt đối không tự động chạy lại mù.
- **Cửa sổ quan sát sau phát hành (§15.3)**: Theo dõi health check, error rate, p95 latency trong 15 phút đầu. Nếu smoke test fail → chuyển trạng thái `RELEASE_FAILED` và rollback ứng dụng về digest liền trước.
