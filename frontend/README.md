# Cổng Web Portal Học Đường & Quản Trị (AuthShield-LMS)

Ứng dụng Single Page Application (SPA) xây dựng trên nền tảng React 18, Vite, TypeScript và Tailwind CSS:

## Đặc điểm kiến trúc:
- Tách bạch giao diện thành 4 Không gian làm việc (`workspaces/`):
  * `admin/`: Góc Quản trị viên kỹ thuật.
  * `board/`: Góc Ban Giám hiệu điều hành & phê duyệt.
  * `teacher/`: Góc Giáo viên giảng dạy & chủ nhiệm.
  * `student/`: Góc Học sinh học tập & dịch vụ.
- Tích hợp thành phần `workspace-switcher/` cho phép người kiêm nhiệm chuyển đổi ngữ cảnh làm việc mượt mà và an toàn.
- Dịch vụ gọi API (`services/`) tự động gắn Token ngữ cảnh và kiểm soát cấp độ xác thực acr S1/S2/S3.
