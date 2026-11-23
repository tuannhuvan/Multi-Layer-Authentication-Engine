# UI Baseline & Bảng Trạng Thái Giao Diện (§12.1)

- **UI Baseline ID**: `UI-002`
- **Viewports kiểm chứng bắt buộc**: `1440px` (Desktop), `768px` (Tablet), `390px` (Mobile)

## Bảng trạng thái tối thiểu cho mọi màn hình (§12.1)
| Trạng thái | Yêu cầu bắt buộc |
| :--- | :--- |
| **Đang tải (Loading)** | Hiển thị Skeleton cố định kích thước, không nhảy bố cục (CLS = 0) |
| **Rỗng (Empty)** | Thông điệp rõ ràng + nút/hành động tiếp theo |
| **Lỗi (Error)** | Thông điệp dễ hiểu, hiển thị mã tra cứu (`traceId`), có nút Thử lại |
| **Hết phiên (Session Expired / Step-up)** | Giữ nguyên dữ liệu đang nhập trên form, mở modal xác thực lại/nâng cấp S2/S3 rồi quay về đúng chỗ |
| **Thiếu quyền (Forbidden)** | Ẩn/khóa thao tác theo role & workspace; trang/thông báo `403` rõ ràng |
| **Validation** | Báo lỗi theo từng trường (inline), không xóa mất dữ liệu người dùng đã nhập |
