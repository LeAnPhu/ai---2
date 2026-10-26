# Review Gate 2 — AgriStock

Ngày kiểm tra: 2026-10-26. Dữ liệu thử là giả lập, không có dữ liệu nông hộ.

## 1. Bằng chứng quy trình RED → GREEN
- **RED (test first):** tạo `SPEC.md`, `AGENTS.md`, `tests/test_app.py`, chạy `python -m unittest discover -s tests -v` khi chưa có `app.py`. Lệnh trả exit code 1, `ModuleNotFoundError: No module named 'app'`. Có log ở `red-log.txt`.
- **GREEN (implementation):** tạo `app.py` bám Spec, chạy lại lệnh. Exit code 0: **15 tests, OK**. Log lưu tại `green-log.txt`.
- **Giới hạn chứng cứ:** RED này chứng minh test tồn tại trước implementation, nhưng chưa chứng minh từng test riêng lẻ có thể bắt được từng bug trong một bản code lỗi.

## 2. Checklist Review
| Nhóm | Câu hỏi | Kết quả | Bằng chứng |
|---|---|---|---|
| Correctness | Không cho phép xuất âm? | PASS | `test_out_of_stock_does_not_mutate_BR05` |
| Correctness | Giao dịch nhập + xuất cập nhật đúng tồn? | PASS | `test_in_out_and_exact_zero_BR05_BR07` |
| Correctness | Retry không tính kho hai lần? | PASS | `test_duplicate_id_same_payload_safe_BR08` |
| Correctness | Concurrent retry cập nhật nguyên tử? | PASS | `test_concurrent_retry_atomic_BR07_BR08` |
| Correctness | Tránh vượt giới hạn kho? | PASS | `test_capacity_limit_BR06` |
| Security | API yêu cầu key? | PASS | `test_auth_health_and_empty_BR01_BR12`; `hmac.compare_digest` |
| Security | Không hard-code key? | PASS | `APP_API_KEY` từ biến môi trường |
| Security | Không in stack trace cho client? | PASS qua code review | `INTERNAL_ERROR` trả thông điệp chung |
| Security | Không ghi log body / API key? | PASS qua code review | `log_message` bị vô hiệu hóa |
| Consistency | Error code khớp Spec? | PASS cho các nhánh test | Nhóm validation + HTTP tests |
| Consistency | Kho rỗng là `200`, không `404`? | PASS | `test_empty_inventory_and_history_BR12` |
| Consistency | Ngoài Spec bị từ chối? | PASS qua code review | Không có database, web UI, đa kho |

## 3. Hai thiếu sót được review phát hiện và cách sửa **qua Spec**
**FINDING-01 — Boolean bị tính nhầm thành 1 kg (Correctness / Security, severity: Medium)**
- Rủi ro trong Python: `isinstance(True, int)` là `True`, dễ để API chấp nhận `true` như `1` nếu chỉ dùng kiểm tra số nguyên thông thường.
- **Sửa Spec trước:** bổ sung câu `bool ... → 422 INVALID_QUANTITY` vào BR-04, bổ sung `SPEC-REV-01`.
- **Test từ Spec:** `test_boolean_quantity_rejected`.
- **Cách sửa code:** dùng `type(qty) is int`, không dùng `isinstance(qty, int)`.
- **Xác nhận:** test PASS. Đây là **rủi ro phát hiện từ review**, không phải khẳng định đã chạy một bản code lỗi trước đó.

**FINDING-02 — Trùng `request_id` nhưng khác ghi chú vẫn được trả kết quả cũ (Consistency / Correctness, severity: High)**
- Rủi ro: kiểm tra gửi trùng chỉ dựa vào `type/item/quantity` sẽ bỏ qua việc client sửa `note`, khiến nội dung giao dịch hiển thị không khớp thao tác mới.
- **Sửa Spec trước:** BR-08 quy định nội dung so khớp bắt buộc có `note` và `actor`; bổ sung `SPEC-REV-02`.
- **Test từ Spec:** `test_duplicate_id_changed_note_conflict`.
- **Cách sửa code:** lưu fingerprint tuple `(type, item_code, quantity_kg, note, actor)` và trả `409 DUPLICATE_REQUEST_ID` khi khác.
- **Xác nhận:** test PASS. Đây là **thiếu sót thiết kế được ngăn ngừa**, không phải lỗi production đã xảy ra.

## 4. Vấn đề còn lại và Out of Scope
- API key minh họa chỉ phù hợp môi trường local; triển khai thật cần TLS, quản lý secrets, rotation và xác thực/ủy quyền từng người dùng.
- Dữ liệu đang ở RAM nên khởi động lại sẽ mất, không sử dụng cho quản lý kho thật.
- Chưa có rate limiting, audit log bền vững, kiểm thử tải, persistence, CORS và phân trang lịch sử.
- Health công khai; không chứa thông tin nhạy cảm.
- Phân tích này không phải chứng nhận bảo mật cho môi trường production.

## 5. Gate 2 — Kết luận
- [x] Tài liệu Spec có các BR xác định và mã lỗi cụ thể.
- [x] Có red-log và green-log kiểm chứng thứ tự test trước code.
- [x] Một lát cắt nghiệp vụ API chạy qua HTTP thực, không chỉ mock.
- [x] 15 test PASS.
- [x] Review theo Correctness, Security, Consistency.
- [x] Có tối thiểu 2 phát hiện và sửa thông qua Spec + test + code.
- [x] Không dùng dữ liệu thật, không thêm tính năng ngoài Spec.
