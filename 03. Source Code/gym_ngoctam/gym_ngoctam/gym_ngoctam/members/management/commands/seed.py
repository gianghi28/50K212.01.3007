from datetime import timedelta


from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from members.models import (
    BaoLuu, DangKyGoi, GoiTap, HoiVien, LuotCheckin, TaiKhoan, ThanhToan, VeLe, YeuCauCheckin,
)

GOI_MAU = [
    # tenGoi, thoiHan (ngày), gia, thoiHanBaoLuu (ngày)
    ("1 tháng", 30, 300000, 7),
    ("3 tháng", 90, 800000, 30),
    ("6 tháng", 180, 1500000, 90),
    ("12 tháng", 365, 2800000, 180),
]

# hoTen, soDienThoai, chỉ số gói (None = chưa có gói), số ngày trước khi bắt đầu, đang bảo lưu?
HOI_VIEN_MAU = [
    ("Nguyễn Văn An", "0901234567", 1, 20, False),
    ("Trần Thị Bình", "0912345678", 0, 10, False),
    ("Lê Hoàng Cường", "0923456789", 3, 100, False),
    ("Phạm Minh Dung", "0934567890", 0, 45, False),   # hết hạn
    ("Võ Quốc Em", "0945678901", 2, 30, True),       # đang bảo lưu
    ("Đặng Thu Hà", "0956789012", None, 0, False),   # chưa có gói
]


class Command(BaseCommand):
    help = "Tạo tài khoản quản lý (admin / admin123) và dữ liệu mẫu cho 9 bảng."

    @transaction.atomic
    def handle(self, *args, **options):
        if not TaiKhoan.objects.filter(tenDangNhap="admin").exists():
            TaiKhoan.objects.create_user("admin", "quanly@gymngoctam.vn", "admin123", soDienThoai="0987654321")
            self.stdout.write("Đã tạo tài khoản: admin / admin123")

        if GoiTap.objects.exists():
            self.stdout.write(self.style.WARNING("Đã có dữ liệu mẫu, bỏ qua."))
            return

        bay_gio = timezone.now()
        goi = [GoiTap.objects.create(tenGoi=t, thoiHan=h, gia=g, thoiHanBaoLuu=b) for t, h, g, b in GOI_MAU]
        GoiTap.objects.create(tenGoi="2 tháng", thoiHan=60, gia=550000, thoiHanBaoLuu=15,
                              trangThaiBan=GoiTap.TrangThaiBan.NGUNG_BAN)

        for ho_ten, sdt, i_goi, truoc, bao_luu in HOI_VIEN_MAU:
            ngay_bd = bay_gio - timedelta(days=truoc)
            hv = HoiVien.objects.create(hoTen=ho_ten, soDienThoai=sdt, ngayTao=ngay_bd)
            if i_goi is None:
                continue
            g = goi[i_goi]
            dk = DangKyGoi.objects.create(
                hoiVien=hv, goiTap=g, loai=DangKyGoi.Loai.DANG_KY_MOI, soTien=g.gia,
                ngayDangKy=ngay_bd, ngayBatDau=ngay_bd,
                ngayKetThuc=DangKyGoi.tinh_ngay_ket_thuc(ngay_bd, g.thoiHan),
            )
            ThanhToan.objects.create(
                dangKy=dk, soTien=g.gia, thoiGian=ngay_bd, nhanVienThu="admin",
                hinhThuc=ThanhToan.HinhThuc.CHUYEN_KHOAN if truoc % 2 else ThanhToan.HinhThuc.TIEN_MAT,
            )
            if bao_luu:
                bd_bl = bay_gio - timedelta(days=5)
                BaoLuu.objects.create(dangKy=dk, ngayBatDau=bd_bl, ngayKetThuc=bd_bl + timedelta(days=g.thoiHanBaoLuu),
                                      soNgayDaDung=5)
                # trong lúc bảo lưu, ngày kết thúc gói được lùi thêm đúng số ngày bảo lưu
                dk.ngayKetThuc += timedelta(days=g.thoiHanBaoLuu)
                dk.save()
            else:
                yc = YeuCauCheckin.objects.create(hoiVien=hv, thoiGianGui=bay_gio - timedelta(hours=truoc),
                                                  trangThai=YeuCauCheckin.TrangThai.DA_XAC_NHAN)
                con_han = dk.ngayKetThuc >= yc.thoiGianGui
                LuotCheckin.objects.create(
                    yeuCau=yc, hoiVien=hv, thoiGian=yc.thoiGianGui + timedelta(minutes=1),
                    ketQua=LuotCheckin.KetQua.THANH_CONG if con_han else LuotCheckin.KetQua.KHONG_THANH_CONG,
                )

        for ho_ten, sdt in [("Khách vãng lai", None), ("Bùi Văn Khoa", "0967890123")]:
            gd = ThanhToan.objects.create(soTien=VeLe.GIA_MAC_DINH, hinhThuc=ThanhToan.HinhThuc.TIEN_MAT,
                                          nhanVienThu="admin")
            VeLe.objects.create(giaoDich=gd, hoTen=None if sdt is None else ho_ten, soDienThoai=sdt)

        self.stdout.write(self.style.SUCCESS("Xong dữ liệu mẫu. Chạy: python manage.py runserver"))
