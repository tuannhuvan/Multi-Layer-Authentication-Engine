# Test Plan: US-012 (Baseline `TEST-US-012-004`)

- **Story ID**: `US-012`
- **Risk Level**: `HIGH`
- **Test Baseline ID**: `TEST-US-012-004`
- **Golden Dataset**: `docs/spec/golden/grade_calculation_golden.csv`
- **Fixtures**: `tests/fixtures/us012_fixtures.json`

## Danh sách ca kiểm thử bắt buộc (Niêm phong ở P3)
1. `test_ac012_01_golden_calculation`: Đối chiếu toàn bộ 5 dòng dữ liệu đối chứng trong `grade_calculation_golden.csv`.
2. `test_ac012_02_anti_idor_unit_scope`: Kiểm thử giáo viên lớp `10A1` cập nhật điểm lớp `10A2` bị chặn `403 UNIT_SCOPE_FORBIDDEN` kèm `traceId`.
3. `test_ac012_03_require_acr_s3_signature`: Kiểm thử Ban Giám hiệu ký duyệt với `ACR=S2` bị chặn `403 STEP_UP_S3_REQUIRED`, và `ACR=S3` thành công.
4. `test_ac012_04_exempt_zero_weight`: Kiểm thử học sinh miễn trừ cột điểm `tx2` (`exempt_tx2=true`) chia đúng mẫu số 6.
