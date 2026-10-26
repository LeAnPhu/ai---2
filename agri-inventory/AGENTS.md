# AGENTS — Quy ước cho AI coding agent

## Stack
- Python 3.11+, standard library only (`http.server`, `json`, `threading`, `unittest`).
- Giao diện HTTP JSON. Không framework, không database, không giao diện web.
- Source: `app.py`; tests: `tests/test_app.py`; hướng dẫn: `README.md`.

## Quy ước
1. Đọc `SPEC.md` trước khi sửa code. Ghi mã BR tương ứng trong tên hoặc docstring của mỗi nhóm test.
2. TDD: viết test trước (RED), triển khai tối thiểu (GREEN), sau đó refactor khi vẫn PASS.
3. Validation đặt trong service để test độc lập HTTP; route layer chỉ parse/auth/serialize.
4. Response thành công/ lỗi phải giữ schema trong SPEC. Không thay đổi contract âm thầm.
5. Dùng integer kg; không float/Decimal trong MVP. Không chấp nhận `bool` là `int`.
6. Dùng lock bảo vệ cập nhật tồn, lịch sử và bảng idempotency.
7. Không in secret, không ghi payload nhạy cảm vào log; dữ liệu chỉ là demo.

## Điều KHÔNG làm
- Không thêm tính năng ngoài Spec (đơn hàng, kho mới, dashboard, upload file).
- Không thêm thư viện từ pip hay gọi dịch vụ/LLM/network bên ngoài khi chạy test.
- Không lưu dữ liệu người dùng thật, không commit API key, không bypass auth để test production.
- Không tự sửa test chỉ để hợp thức hóa một bug đang có; sửa logic hoặc cập nhật Spec được duyệt trước.
- Không gộp nhiều loại lỗi thành HTTP 200 hay nuốt lỗi và trả thành công giả.

## Quy trình và điều kiện hoàn tất
- Gate 1: Spec rõ BR, error code, edge cases và out-of-scope.
- RED: test thất bại khi chưa có implementation; ghi bằng chứng vào `review-notes.md`.
- GREEN: tối thiểu một endpoint đi hết từ HTTP đến service; toàn bộ test PASS.
- Gate 2: review Correctness / Security / Consistency, chứng minh >=2 lỗi tiềm tàng, diễn giải sửa qua Spec.
- Run: `python -m unittest discover -s tests -v`.
