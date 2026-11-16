# API Gateway Service (Policy Enforcement Point - PEP)

Phân lớp chốt chặn biên bảo vệ hệ thống:
- Kiểm tra tính hợp lệ và chữ ký số của Token JWT.
- Cưỡng chế cấp độ xác thực bảo đảm `acr` (S1, S2, S3).
- Lọc lưu lượng bất thường thông qua WAF và Rate Limiting.
- Chặn đứng tấn công vượt quyền ngang/dọc (Anti-IDOR Guard) bằng cách xác thực header `X-Workspace-Context`.
