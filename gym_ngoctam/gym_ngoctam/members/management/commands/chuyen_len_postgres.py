"""Chuyển toàn bộ dữ liệu từ db.sqlite3 (máy cá nhân) lên Postgres (Neon) để chạy trên Vercel.

Cách chạy (PowerShell, trong thư mục có manage.py):
    $env:DATABASE_URL="<chuỗi kết nối Postgres lấy trên Vercel>"
    python manage.py migrate
    python manage.py chuyen_len_postgres
Lệnh xóa sạch dữ liệu đang có trên Postgres rồi chép lại từ db.sqlite3, kèm ảnh hội viên trong thư mục media.
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from members.models import (BaoLuu, DangKyGoi, GoiTap, HoiVien, LuotCheckin, TaiKhoan, TepTin,
                            ThanhToan, VeLe, YeuCauCheckin)

# Thứ tự cha trước, con sau để không vướng khóa ngoại
CAC_BANG = [TaiKhoan, GoiTap, HoiVien, DangKyGoi, ThanhToan, VeLe, BaoLuu, YeuCauCheckin, LuotCheckin]


class Command(BaseCommand):
    help = "Chép dữ liệu từ db.sqlite3 lên Postgres (Vercel)."

    def handle(self, *args, **options):
        if "cu" not in settings.DATABASES:
            raise CommandError("Chưa đặt biến DATABASE_URL. Xem hướng dẫn ở đầu file chuyen_len_postgres.py")

        with transaction.atomic(using="default"):
            for m in reversed(CAC_BANG):
                m._base_manager.using("default").all().delete()
            TepTin.objects.using("default").all().delete()

            for m in CAC_BANG:
                ds = list(m._base_manager.using("cu").all())
                for o in ds:
                    o._state.db = "default"
                    o._state.adding = True
                m._base_manager.using("default").bulk_create(ds, batch_size=200)
                self.stdout.write(f"  {m._meta.db_table}: {len(ds)} dòng")

            so_anh = 0
            for hv in HoiVien._base_manager.using("cu").exclude(anhDaiDien="").exclude(anhDaiDien__isnull=True):
                ten = hv.anhDaiDien.name
                duong_dan = settings.MEDIA_ROOT / ten
                if duong_dan.exists():
                    TepTin.objects.using("default").create(ten=ten, noiDung=duong_dan.read_bytes())
                    so_anh += 1
            self.stdout.write(f"  Ảnh hội viên: {so_anh} file")

        self.stdout.write(self.style.SUCCESS("Đã chuyển xong dữ liệu lên Postgres."))
