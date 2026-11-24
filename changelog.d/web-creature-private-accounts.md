---
bump: minor
title: WEB CREATURE private account foundation
---
## vi
### Thêm mới
- **Tài khoản riêng tư.** Thêm kho tài khoản SQLite với khởi tạo owner một lần qua thiết lập cục bộ đáng tin cậy.
- **Lời mời.** Owner có thể tạo và thu hồi lời mời; chấp nhận lời mời và tạo tài khoản thành viên trong một giao dịch nguyên tử.
- **Đăng nhập.** Băm mật khẩu bằng scrypt với salt riêng; phản hồi đăng nhập thất bại chung; session token ngẫu nhiên chỉ lưu bản băm, có hạn dùng và thu hồi.
- **Phạm vi người dùng.** API tra cứu session trả về danh tính tài khoản để host áp dụng kiểm tra quyền sở hữu theo từng yêu cầu.

### Bảo mật
- Không có endpoint bootstrap owner công khai hoặc đăng ký công khai.
- Đây chưa phải website đăng nhập hoàn chỉnh. Host vẫn phải triển khai TLS, cookie HttpOnly/Secure/SameSite, CSRF, giới hạn tốc độ, xoay vòng session, email delivery/verification nếu cần, backup và phân quyền theo user cho mọi dữ liệu.

## en
### Added
- **Private accounts.** Added a SQLite account store with one-time owner bootstrap through trusted local setup.
- **Invitations.** Owners can issue and revoke invitations; acceptance and member creation occur in one atomic transaction.
- **Authentication primitives.** Passwords use scrypt with per-account salts; login failures are generic; opaque random session tokens are stored only as hashes, with expiry and revocation.
- **User scope.** Session resolution returns account identity for host-enforced per-request ownership checks.

### Security
- No public owner-bootstrap endpoint or public self-registration.
- This is not yet a complete login website. The host must still implement TLS, HttpOnly/Secure/SameSite cookies, CSRF protection, rate limiting, session rotation, email delivery/verification if needed, backups and per-user authorization for all data.
