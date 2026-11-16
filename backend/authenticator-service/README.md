# Authenticator Service (IdP & PDP)

Cổng xác thực tập trung và máy chủ quyết định chính sách truy cập:
- Hỗ trợ giao thức OpenID Connect (OIDC), OAuth 2.1 và PKCE.
- Cơ chế khóa tài khoản lũy tiến (Progressive Account Lockout) chống Brute-force.
- Động cơ xác thực 3 cấp độ:
  * S1: Mật khẩu + CAPTCHA (Phiên 8 giờ).
  * S2: Mật khẩu + TOTP / SMS OTP (Phiên 4 giờ).
  * S3: Mật khẩu + Ký số Soft-HSM / PKI FIDO2 (Phiên 15 phút, yêu cầu mã PIN).
- Quản trị định danh và đồng bộ tài khoản tự động qua SCIM 2.0.
- Cấp phát Token ngữ cảnh cho cơ chế Workspace Switcher mà không nhân bản vai trò.
