---
bump: minor
title: WEB CREATURE knowledge verification and goal-driven research
---
## vi
### Thêm mới
- **Báo cáo nghiên cứu được lưu riêng khỏi bộ nhớ ngữ nghĩa.** Giữ lại câu hỏi, nguồn, dấu thời gian và mã băm nội dung.
- **Phân loại bằng chứng không đồng nghĩa với xác minh sự thật.** Câu trùng giữa các nguồn được đánh dấu là có đối chiếu; câu chỉ xuất hiện ở một nguồn được đánh dấu là đơn nguồn.
- **Xác minh cần người đánh giá rõ ràng.** Lưu người đánh giá, quyết định, lý do và thời điểm; không tự động nâng dữ liệu web thành kiến thức đã xác minh.
- **Nâng cấp kiến thức vào bộ nhớ là thao tác riêng.** Yêu cầu quyền xác minh, quyền nâng cấp và quyền ghi bộ nhớ.
- **Nghiên cứu theo mục tiêu được gọi thủ công.** Chỉ chạy khi mục tiêu đang hoạt động và host cấp đủ capability.

### Bảo mật
- **Không có bộ tìm kiếm Internet trực tiếp hoặc bộ lập lịch tự động.** Search/transport vẫn phải do host tin cậy cung cấp.
- **Không tự phát hiện mâu thuẫn ngữ nghĩa hoặc xác nhận sự thật.** Việc đối chiếu hiện tại chỉ là so sánh câu chính xác.

## en
### Added
- **Research reports are persisted separately from semantic memory.** Reports retain the question, source provenance, retrieval timestamps and content hashes.
- **Evidence classification is not factual verification.** Exact statements shared across sources are labelled corroborated; source-unique statements are labelled single-source.
- **Verification requires an explicit human review.** Reviewer, decision, rationale and timestamp are recorded; web content is never auto-promoted to verified knowledge.
- **Knowledge promotion is a separate operation.** It requires independent verification, promotion and memory-write capabilities.
- **Goal-driven research is manually invoked.** The target goal must already be active and the host must grant the required capabilities.

### Security
- **No live search provider or autonomous scheduler is bundled.** Search and network transport remain host-injected.
- **No semantic contradiction detection or automatic truth assertion is claimed.** Current comparison is deterministic exact-statement matching.
