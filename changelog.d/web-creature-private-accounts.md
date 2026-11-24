---
bump: minor
title: WEB CREATURE private account store
---
## vi
### Thêm mới
- **Tài khoản riêng tư.** Thêm lưu trữ tài khoản SQLite, bootstrap chủ sở hữu một lần, mật khẩu PBKDF2 và email chuẩn hóa.
- **Đăng ký theo lời mời.** Thêm token lời mời ngẫu nhiên, chỉ lưu SHA-256, có hạn dùng, thu hồi, giới hạn lượt dùng và tiêu thụ nguyên tử.
- **Phiên đăng nhập.** Thêm token phiên ngẫu nhiên, chỉ lưu hash, có thời hạn, thu hồi từng phiên và thu hồi toàn bộ phiên thành viên bởi chủ sở hữu.
- **Kiểm thử.** Thêm kiểm thử cho bootstrap, đăng ký, quyền chủ sở hữu, xác thực và thu hồi phiên.

### Bảo mật
- Đây là lớp lưu trữ/domain, chưa phải API đăng nhập production.
- Chưa có HTTPS, cookie bảo mật, CSRF, rate limiting, email verification/reset, giao diện web hoặc triển khai.
- Bootstrap chủ sở hữu chỉ dành cho công cụ thiết lập tin cậy, không được đưa ra endpoint công khai.

## en
### Added
- **Private accounts.** Adds SQLite account storage, one-time owner bootstrap, PBKDF2 password hashing and normalized unique email addresses.
- **Invitation-only registration.** Adds random invitation tokens, SHA-256-only persistence, expiry, revocation, use limits and atomic consumption.
- **Login sessions.** Adds opaque random session tokens, hash-only persistence, expiry, individual revocation and owner-controlled member-session revocation.
- **Tests.** Adds coverage for bootstrap, registration, owner permissions, authentication and session revocation.

### Security
- This is a domain persistence layer, not a production login API.
- HTTPS, secure cookies, CSRF, rate limiting, email verification/recovery, web UI and deployment are not included.
- Owner bootstrap is for a trusted setup command only and must never be exposed as a public endpoint.
