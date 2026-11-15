"""UC02.3 – TH2: quét và tự động xóa (mềm) hội viên không hoạt động quá 5 tháng.

Chạy tay:   python manage.py don_dep_hoi_vien
Chạy tự động lúc 00:00 mỗi ngày: đăng ký file don_dep_hang_ngay.bat trong Task Scheduler (xem README).
Kết quả được ghi vào logs/gym.log.
"""
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from members import nghiep_vu as nv
from members.models import ket_thuc_bao_luu_het_han


class Command(BaseCommand):
    help = "Tự động xóa hội viên không còn hạn, không bảo lưu và không hoạt động quá 5 tháng."

    def handle(self, *args, **options):
        ket_thuc_bao_luu_het_han()  # cập nhật bảo lưu hết hạn trước khi xét
        da_xoa = nv.don_dep_hoi_vien_khong_hoat_dong()
        (settings.BASE_DIR / "logs").mkdir(exist_ok=True)
        (settings.BASE_DIR / "logs" / "don_dep_lan_cuoi.txt").write_text(
            timezone.now().date().isoformat(), encoding="utf-8")
        if da_xoa:
            self.stdout.write(self.style.SUCCESS(f"Đã xóa {len(da_xoa)} hội viên: {', '.join(da_xoa)}"))
        else:
            self.stdout.write("Không có hội viên nào cần xóa.")
