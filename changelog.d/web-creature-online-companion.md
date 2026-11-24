---
bump: minor
title: WEB CREATURE online companion foundation
---
## vi
### Thêm mới
- **Nền tảng độc lập.** Xác định WEB CREATURE là website riêng kết hợp Windows Desktop Agent, truy cập riêng tư theo lời mời.
- **Hợp đồng hội thoại.** Thêm session/message models độc lập với nhà cung cấp AI.
- **Quản lý chủ động.** Thêm cấu hình thông báo do người dùng kiểm soát; mặc định tắt.
- **Đề xuất hành động.** Thêm action classes và approval fingerprint gắn với đúng mục tiêu và payload; hành động bị hạn chế luôn bị từ chối.
- **Lời mời an toàn.** Token ngẫu nhiên mạnh, chỉ lưu SHA-256, mặc định dùng một lần, có thời hạn và có thể thu hồi.

### Bảo mật
- Các hợp đồng này không tự tạo API, đăng nhập, session, kết nối mạng hoặc quyền điều khiển máy tính.
- ApoloniaAI và Apokolips vẫn là các dự án riêng; không có tích hợp ngầm.
- Xác thực host, lưu trữ nguyên tử, giới hạn tốc độ, ghép nối thiết bị và phân quyền theo người dùng vẫn cần triển khai.

## en
### Added
- **Independent product topology.** Defines WEB CREATURE as a private invitation-only website plus a paired Windows Desktop Agent.
- **Conversation contracts.** Adds provider-neutral session and message models.
- **Managed initiative.** Adds user-controlled notification preferences, disabled by default.
- **Action proposals.** Adds action classes and an approval fingerprint bound to the exact target and payload; restricted actions remain denied.
- **Secure invitations.** Adds high-entropy invitation tokens, SHA-256-only storage representation, single-use default, expiry and revocation.

### Security
- These contracts do not create HTTP APIs, authentication, sessions, network connections or computer-control permissions.
- ApoloniaAI and Apokolips remain separate projects; no implicit integration is introduced.
- Host authentication, atomic persistence, rate limiting, device pairing and per-user authorization remain to be implemented.
