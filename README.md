# AgriStock — bài thực hành Spec-Driven Development

Ứng dụng mẫu mini REST API nhập/xuất kho phân bón của hợp tác xã. Dữ liệu giả lập, reset khi tắt server.

## Danh sách file
- `SPEC.md`: quy tắc nghiệp vụ, API, edge cases, out of scope, định nghĩa trạng thái.
- `AGENTS.md`: stack, quy ước và giới hạn AI.
- `tests/test_app.py`: tests được viết **trước** code.
- `app.py`: service + API stdlib Python.
- `review-notes.md`: checklist Gate 2 và 2 finding được giải quyết qua Spec.
- `red-log.txt`, `green-log.txt`: bằng chứng RED/GREEN.

## Chạy test
Yêu cầu Python 3.11+; không cài thêm package.

```bash
python -m unittest discover -s tests -v
```

Kết quả đã quan sát: `Ran 15 tests ... OK`.

## Chạy server
**Linux/macOS:**
```bash
export APP_API_KEY='local-demo-key-only'
python app.py
```
**Windows PowerShell:**
```powershell
$env:APP_API_KEY='local-demo-key-only'
python app.py
```

Server mặc định `http://127.0.0.1:8000`. Có thể chỉnh `PORT` bằng biến môi trường.

## Demo API bằng curl
1. Tình trạng:
```bash
curl http://127.0.0.1:8000/health
```
2. Xem tồn kho ban đầu:
```bash
curl -H 'X-API-Key: local-demo-key-only' http://127.0.0.1:8000/inventory
```
3. Nhập 50 kg:
```bash
curl -X POST http://127.0.0.1:8000/transactions \
  -H 'X-API-Key: local-demo-key-only' -H 'Content-Type: application/json' \
  -d '{"request_id":"DEMO-0001","type":"IN","item_code":"PB-NPK16","quantity_kg":50,"note":"Nhap demo"}'
```
4. Xuất 15 kg:
```bash
curl -X POST http://127.0.0.1:8000/transactions \
  -H 'X-API-Key: local-demo-key-only' -H 'Content-Type: application/json' \
  -d '{"request_id":"DEMO-0002","type":"OUT","item_code":"PB-NPK16","quantity_kg":15}'
```
5. Xem tồn 35 kg:
```bash
curl -H 'X-API-Key: local-demo-key-only' http://127.0.0.1:8000/inventory
```
6. Gửi lại request `DEMO-0002` đúng payload: 200 và tồn không giảm lần nữa.
7. Đổi số lượng khi vẫn dùng `DEMO-0002`: 409 `DUPLICATE_REQUEST_ID`.

## Chú ý
- Không sử dụng dữ liệu hoặc khóa thật; ứng dụng chỉ dành cho học tập và chạy local.
- Không mở port ra Internet hay xem đây là giải pháp kho production.
- Quy trình đề xuất: sửa **SPEC.md → thêm/sửa test → xem RED → sửa code → GREEN → review**.
