"""Đổi tên đăng nhập của tài khoản quản lý.

Cách dùng:  python manage.py doi_ten_dang_nhap <tên_cũ> <tên_mới>
Ví dụ:      python manage.py doi_ten_dang_nhap admin ngoctam
"""
from django.contrib.admin.models import LogEntry
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from members.models import TaiKhoan


class Command(BaseCommand):
    help = "Đổi tên đăng nhập của tài khoản quản lý (mật khẩu giữ nguyên)."

    def add_arguments(self, parser):
        parser.add_argument("ten_cu")
        parser.add_argument("ten_moi")

    @transaction.atomic
    def handle(self, ten_cu, ten_moi, **options):
        ten_moi = ten_moi.strip()
        if not ten_moi or len(ten_moi) > 100 or " " in ten_moi:
            raise CommandError("Tên đăng nhập mới không hợp lệ (không để trống, không có dấu cách, tối đa 100 ký tự).")
        if not TaiKhoan.objects.filter(pk=ten_cu).exists():
            raise CommandError(f"Không có tài khoản '{ten_cu}'. Các tài khoản hiện có: "
                               + ", ".join(TaiKhoan.objects.values_list("pk", flat=True)))
        if TaiKhoan.objects.filter(pk=ten_moi).exists():
            raise CommandError(f"Tên đăng nhập '{ten_moi}' đã tồn tại.")
        # tenDangNhap là khóa chính → cập nhật trực tiếp, kèm nhật ký trang /admin/ đang tham chiếu tới nó
        TaiKhoan.objects.filter(pk=ten_cu).update(tenDangNhap=ten_moi)
        LogEntry.objects.filter(user_id=ten_cu).update(user_id=ten_moi)
        self.stdout.write(self.style.SUCCESS(
            f"Đã đổi tên đăng nhập '{ten_cu}' → '{ten_moi}'. Mật khẩu giữ nguyên. Hãy đăng nhập lại."))
