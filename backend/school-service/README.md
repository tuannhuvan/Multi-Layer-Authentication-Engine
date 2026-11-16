# School Management Service (Business Tier)

Tầng xử lý logic nghiệp vụ trường học xây dựng trên Spring Boot:
- `admin/`: Khởi tạo năm học, khối lớp, phân quyền tài khoản, nhập xuất Excel hàng loạt.
- `board/`: Dashboard giám sát toàn trường, phê duyệt TKB, duyệt mở khóa sửa điểm (Checker SoD), ký số học bạ (S3).
- `teacher/`: Điểm danh theo tiết, ghi sổ đầu bài, nhập điểm (S2), khóa điểm (S3), gửi đơn đề nghị sửa điểm (Maker).
- `student/`: Tra cứu điểm số cá nhân, nộp bài tập (tính phạt nộp muộn), đơn nghỉ học, theo dõi học phí.
- `audit/`: Ghi nhận nhật ký kiểm toán bất biến chuỗi băm HMAC (WORM Audit Log).
