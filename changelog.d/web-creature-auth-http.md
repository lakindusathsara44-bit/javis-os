---
bump: minor
title: WEB CREATURE private authentication HTTP adapter
---
## vi
### Thêm mới
- **HTTP authentication router.** Thêm FastAPI router có thể gắn vào host, gồm đăng ký bằng lời mời, đăng nhập, đăng xuất, tài khoản hiện tại và quản lý lời mời cho chủ sở hữu.
- **Cookie an toàn.** Dùng cookie phiên Secure/HttpOnly/SameSite=Strict trong production và prefix `__Host-`.
- **Bảo vệ request.** Yêu cầu exact Origin, custom request header và rate limiter do host cung cấp; từ chối khi rate limiter lỗi.
- **Không có bootstrap công khai.** Không tạo endpoint khởi tạo owner hoặc đăng ký công khai.

### Bảo mật
- Router chưa được mount vào một ứng dụng production và chưa có domain/deployment.
- Rate limiter thực tế, email verification/recovery, headers, proxy trust và security review vẫn cần hoàn tất.

## en
### Added
- **HTTP authentication router.** Adds a host-mountable FastAPI router for invitation registration, login, logout, current-account lookup and owner invitation management.
- **Secure cookies.** Uses Secure/HttpOnly/SameSite=Strict production session cookies with the `__Host-` prefix.
- **Request protection.** Requires exact Origin, a custom request header and a host-provided rate limiter; fails closed when the limiter fails.
- **No public bootstrap.** No HTTP owner-bootstrap or public self-registration endpoint is provided.

### Security
- The router is not yet mounted in a production application and no domain/deployment is configured.
- A real rate limiter, email verification/recovery, security headers, proxy trust and security review remain required.
