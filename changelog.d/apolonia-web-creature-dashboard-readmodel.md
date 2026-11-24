---
bump: minor
title: WEB CREATURE privacy-safe dashboard read model
---
## vi
### Thêm mới
- **Ảnh chụp trạng thái chỉ đọc cho dashboard.** Hiển thị danh tính, trạng thái vòng đời, số lượng tổng hợp của sự kiện, bộ nhớ, báo cáo nghiên cứu, lượt duyệt kiến thức và trạng thái mục tiêu.
- **Giảm thiểu dữ liệu riêng tư.** Không đưa nội dung bộ nhớ, trích đoạn nghiên cứu, lý do duyệt hoặc payload sự kiện vào snapshot.
- **Quyền riêng biệt.** Việc đọc dashboard yêu cầu capability `dashboard.read`; mặc định bị từ chối.
- **Không tự động tích hợp web.** Không tạo route HTTP, server hoặc background task khi import package.

## en
### Added
- **Read-only dashboard snapshot.** Exposes identity, lifecycle state, aggregate event/memory/research/review counts, goal-state counts and latest event metadata.
- **Privacy-minimized output.** Memory content, research excerpts, review rationale and event payloads are excluded.
- **Separate capability.** Dashboard reads require the explicit `dashboard.read` grant and are denied by default.
- **No implicit web integration.** Importing the package does not mount HTTP routes, start a server or create background tasks.

### Security
- Snapshot reads are observational only and do not mutate Creature state or append audit events.
- Paused, stopped and error states remain visible; no active-state bypass is introduced for write operations.
