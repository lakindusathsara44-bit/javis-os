---
bump: minor
title: WEB CREATURE memory provenance and goal management
---
## vi
### Thêm mới
- **WEB CREATURE lưu trữ ký ức có nguồn gốc rõ ràng.** Bổ sung loại nguồn, trạng thái xác minh, mã băm SHA-256, thẻ và thời hạn lưu trữ tùy chọn.
- **WEB CREATURE quản lý mục tiêu theo trạng thái.** Có thể tạo mục tiêu, đặt mức ưu tiên, tiêu chí hoàn thành và theo dõi tiến độ.

### Cải thiện
- **Tìm kiếm ký ức an toàn hơn.** Có thể lọc theo từ khóa, loại ký ức và trạng thái xác minh; dữ liệu chưa xác minh không tự động trở thành đáng tin cậy.
- **Nâng cấp cơ sở dữ liệu mà không xóa ký ức cũ.** Chuyển đổi SQLite tương thích ngược và bổ sung mã băm cho dữ liệu trước đây.

## en
### Added
- **WEB CREATURE stores memories with clear provenance.** Adds source type, verification status, SHA-256 content hashes, tags and optional retention expiry.
- **WEB CREATURE manages goals through explicit states.** Goals include priority, success criteria and progress tracking.

### Improved
- **Memory retrieval is safer and more useful.** Search supports keywords, memory types and verification filters; unverified data is never promoted automatically.
- **Database upgrades preserve existing memories.** Adds a backward-compatible SQLite migration and hashes for previously stored records.
