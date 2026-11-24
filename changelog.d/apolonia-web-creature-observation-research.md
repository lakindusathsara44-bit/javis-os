---
bump: minor
title: WEB CREATURE local observation and source research
---
## vi
### Thêm mới
- **WEB CREATURE đọc được tài liệu cục bộ trong phạm vi cho phép.** Giới hạn thư mục, loại tệp và kích thước; chặn đường dẫn thoát khỏi thư mục được phê duyệt.
- **WEB CREATURE có nền tảng nghiên cứu nguồn web an toàn.** Chỉ chấp nhận HTTPS trên tên miền được cho phép và kiểm tra từng bước chuyển hướng.
- **Báo cáo nghiên cứu lưu dấu vết nguồn.** Ghi nhận URL cuối, thời điểm truy xuất, loại nội dung và mã băm; so sánh câu trùng lặp và phát hiện nội dung riêng biệt giữa các nguồn.

### Bảo mật
- **Không tự mở kết nối Internet.** Mọi yêu cầu web cần transport do host tin cậy cung cấp, có kiểm soát DNS công khai, TLS, chuyển hướng, thời gian chờ và giới hạn dữ liệu.
- **Quan sát cần quyền riêng biệt.** Đọc tệp cục bộ và nghiên cứu web bị từ chối mặc định nếu host chưa cấp capability tương ứng.

## en
### Added
- **WEB CREATURE can observe approved local documents.** Reads are restricted by configured roots, file extensions and size limits, with path-escape checks.
- **WEB CREATURE has a safer web research foundation.** Only HTTPS URLs on allowlisted domains are accepted, and every redirect is checked.
- **Research reports preserve source provenance.** Records include final URLs, retrieval time, content type and hashes, with shared and source-unique statement comparison.

### Security
- **No implicit Internet connection is opened.** Web requests require a trusted host-provided transport with public-DNS, TLS, redirect, timeout and response-size protections.
- **Observation requires separate capabilities.** Local file reads and web research are denied unless the host explicitly grants the matching capability.
