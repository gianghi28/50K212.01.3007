# Phòng Gym NT – Django (nhóm 50K212.01.3007)

CSDL: SQLite (`db.sqlite3`) – mở bằng **DB Browser for SQLite** (đóng DB Browser trước khi chạy migrate/seed).

## Chạy (đứng trong thư mục có manage.py)
```
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8001
```
Lần đầu tạo dữ liệu mẫu: `python manage.py seed` → đăng nhập **admin / admin123**.

## Các trang
| Chức năng | Đường dẫn |
|---|---|
| Đăng nhập / Quên mật khẩu (UC01) | /dang-nhap/ |
| Quản lý hội viên (UC02) | / |
| Quản lý gói tập (UC03) | /goi-tap/ |
| Check-in – màn quản lý (UC04) | /check-in/ |
| Check-in – màn hội viên quét QR (UC04.3) | /khach/check-in/ (mở trên điện thoại khác) |
| Báo cáo và thống kê (UC05) | /bao-cao/ |
| Trang quản trị dữ liệu | /admin/ |

## Ghi chú
- Mã xác minh "Quên mật khẩu" được **in ra cửa sổ terminal** đang chạy server (bản demo không gửi SMS/email thật).
- Mã QR thanh toán là mã minh họa, tạo qua api.qrserver.com (cần có mạng).
- Xóa hội viên là xóa mềm (cột `daXoa`), dữ liệu doanh thu/lịch sử vẫn giữ.
