# SPEC — Mini API quản lý nhập/xuất kho phân bón hợp tác xã

## 1. Mục tiêu, người dùng và phạm vi
- **Mục tiêu:** giúp thủ kho ghi nhận nhập/xuất phân bón và tra cứu tồn kho chính xác, tránh xuất âm.
- **Người dùng:** thủ kho của một hợp tác xã nhỏ; mỗi thao tác được gắn với một `actor` đã xác thực bằng API key ở tầng HTTP.
- **Lát cắt MVP:** một kho, một loại vật tư tính theo kg, mã cố định `PB-NPK16`, tên `Phân NPK 16-16-8`. Chỉ có một dữ liệu giả lập trong bộ nhớ; không tồn tại sau khi tắt server.
- **API:** `GET /health`, `GET /inventory`, `POST /transactions`, `GET /transactions`; JSON UTF-8; không sử dụng dữ liệu thực tế.
- **Ngoài phạm vi:** đa kho, đa vật tư, giá tiền, đơn hàng, phân quyền nhiều vai trò, cơ sở dữ liệu, giao diện web, tích hợp bên ngoài, hoạt động offline.

## 2. Business Rules (BR)
- **BR-01 — Xác thực:** tất cả đường dẫn nghiệp vụ cần header `X-API-Key` bằng giá trị cấu hình biến môi trường `APP_API_KEY`. Không có/sai key → HTTP 401, `UNAUTHORIZED`; health công khai.
- **BR-02 — Mã vật tư:** `item_code` bắt buộc và chỉ nhận chuỗi chính xác `PB-NPK16`; sai mã → 404 `ITEM_NOT_FOUND`.
- **BR-03 — Loại giao dịch:** `type` chỉ là `IN` hoặc `OUT` (phân biệt chữ hoa/chữ thường). Khác → 422 `INVALID_TYPE`.
- **BR-04 — Số lượng:** `quantity_kg` là số nguyên dương, tối thiểu 1 và tối đa 10.000; bool, số thập phân, chuỗi, 0, âm → 422 `INVALID_QUANTITY`.
- **BR-05 — Xuất kho:** chỉ được xuất khi tồn >= số lượng; nếu không → 409 `INSUFFICIENT_STOCK`, không phát sinh giao dịch.
- **BR-06 — Nhập kho:** tồn sau nhập không vượt quá 1.000.000 kg; vượt → 409 `CAPACITY_EXCEEDED`, không ghi giao dịch.
- **BR-07 — Ghi giao dịch:** giao dịch thành công sinh `id` tăng dần, lưu `type`, `item_code`, `quantity_kg`, `note`, `balance_after_kg` và `actor`; thay đổi số tồn và lưu lịch sử phải là một thao tác nguyên tử dưới khóa.
- **BR-08 — Chống gửi trùng:** `request_id` là chuỗi dài 8–64 ký tự, chỉ chứa chữ ASCII, số, gạch ngang hoặc gạch dưới. Nếu gửi lại *cùng* `request_id` và nội dung nghiệp vụ giống hệt (`type`, `item_code`, `quantity_kg`, `note`, `actor`), trả HTTP 200 cùng kết quả cũ, không trừ/cộng tồn lần hai. Nếu trùng ID mà payload khác → 409 `DUPLICATE_REQUEST_ID`.
- **BR-09 — Ghi chú:** `note` không bắt buộc, mặc định chuỗi rỗng, tối đa 200 ký tự, không chứa ký tự điều khiển; sai → 422 `INVALID_NOTE`. Không dùng khoảng trắng hoặc cắt tự động (note phải được giữ nguyên).
- **BR-10 — Danh tính:** `actor` được server gán cố định là `warehouse-clerk`, client không được gửi trường này. Không có dữ liệu cá nhân thực.
- **BR-11 — Kiểu dữ liệu và schema:** body phải là JSON object; chỉ nhận 5 trường `request_id`, `type`, `item_code`, `quantity_kg`, `note`. Thiếu trường bắt buộc (`request_id`, `type`, `item_code`, `quantity_kg`) → 422 `MISSING_FIELD`; trường dư → 422 `UNKNOWN_FIELD`; body lỗi JSON → 400 `INVALID_JSON`.
- **BR-12 — Danh sách:** `GET /transactions` trả lịch sử theo thứ tự tạo tăng dần. Khi chưa có dữ liệu trả mảng rỗng (200).

## 3. Hợp đồng API và trạng thái
### GET /health
Không cần key. `200 {"status":"ok"}`.

### GET /inventory
Yêu cầu key. Thành công 200:
```json
{"item_code":"PB-NPK16","name":"Phân NPK 16-16-8","unit":"kg","quantity_kg":0}
```
**Empty:** tồn 0 là trạng thái hợp lệ, vẫn trả 200 (không 404). **Loading:** HTTP client đang chờ phản hồi có thể biểu thị loading; backend không trả trạng thái giả. **Error:** 401 khi không xác thực, 500 với lỗi nội bộ không chứa stack trace.

### POST /transactions
Header `Content-Type: application/json`, `X-API-Key` hợp lệ. Ví dụ:
```json
{"request_id":"REQ-0001","type":"IN","item_code":"PB-NPK16","quantity_kg":20,"note":"Nhap kho demo"}
```
**Success:** HTTP 201 (mới) hoặc 200 (gửi lại hợp lệ), cùng kiểu body:
```json
{"id":1,"request_id":"REQ-0001","type":"IN","item_code":"PB-NPK16","quantity_kg":20,"note":"Nhap kho demo","actor":"warehouse-clerk","balance_after_kg":20}
```
**Error:** `{"error":{"code":"INVALID_QUANTITY","message":"quantity_kg must be an integer from 1 to 10000"}}` (HTTP status theo từng BR).

### GET /transactions
Yêu cầu key. `200 {"items":[]}` nếu rỗng; nếu có dữ liệu, `items` là danh sách object cùng schema giao dịch. Không có phân trang trong MVP.

### Mã lỗi HTTP
- 400: `INVALID_JSON`
- 401: `UNAUTHORIZED`
- 404: `NOT_FOUND` (route lạ), `ITEM_NOT_FOUND` (mã vật tư sai)
- 405: `METHOD_NOT_ALLOWED`
- 409: `INSUFFICIENT_STOCK`, `CAPACITY_EXCEEDED`, `DUPLICATE_REQUEST_ID`
- 415: `UNSUPPORTED_MEDIA_TYPE`
- 422: `MISSING_FIELD`, `UNKNOWN_FIELD`, `INVALID_TYPE`, `INVALID_QUANTITY`, `INVALID_NOTE`, `INVALID_REQUEST_ID`
- 500: `INTERNAL_ERROR` (chỉ thông báo chung, không lộ bí mật)

## 4. Edge cases có mã cụ thể
| Trường hợp | Kết quả dự kiến | BR |
|---|---|---|
| Chưa đăng nhập/không có hoặc sai API key | 401 `UNAUTHORIZED` | 01 |
| Kho trống, gọi GET /inventory | 200 `quantity_kg:0` | 12 |
| Kho trống, xuất 1 kg | 409 `INSUFFICIENT_STOCK` | 05 |
| Nhập 10 rồi xuất đúng 10 | 201; tồn 0 | 05, 07 |
| Gửi request_id cũ, cùng payload | 200; tồn và số giao dịch không đổi | 08 |
| Gửi request_id cũ, thay quantity | 409 `DUPLICATE_REQUEST_ID` | 08 |
| quantity_kg là true hoặc 1.5 | 422 `INVALID_QUANTITY` | 04 |
| Body thiếu request_id / chứa field lạ | 422 `MISSING_FIELD` / `UNKNOWN_FIELD` | 11 |
| Sai mã PB-ABC | 404 `ITEM_NOT_FOUND` | 02 |
| Body JSON bị cắt | 400 `INVALID_JSON` | 11 |
| Cộng tồn vượt 1.000.000 | 409 `CAPACITY_EXCEEDED` | 06 |

## 5. Tiêu chí nghiệm thu (Gate 1)
1. Từng BR-01 đến BR-12 có ít nhất một test tự động hoặc kiểm tra hợp đồng rõ ràng.
2. Test viết và chạy RED trước khi có code hiện thực; chỉ triển khai sau khi thấy fail do thiếu module.
3. `python -m unittest discover -s tests -v` chạy PASS không cần internet hay thư viện ngoài.
4. Response lỗi đúng status/code; hành động lỗi không làm thay đổi tồn.
5. Bí mật không hard-code trong mã nguồn; không chứa dữ liệu nông hộ thật.
6. Các đề xuất ngoài Spec phải bị từ chối hoặc sửa Spec + test trước khi thêm code.

## 6. Thay đổi từ Review Gate 2
- **SPEC-REV-01:** xác định rõ boolean `true` không được xem là số lượng `1` (BR-04); thêm test `test_boolean_quantity_rejected`.
- **SPEC-REV-02:** xác định trùng request_id nhưng khác `note` cũng là xung đột, không được bỏ qua trường note (BR-08); thêm test `test_duplicate_id_changed_note_conflict`.
