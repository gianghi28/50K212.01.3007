"""Trang /admin/ để xem nhanh dữ liệu 9 bảng khi test (không phải giao diện chính)."""
from django.contrib import admin

from .models import BaoLuu, DangKyGoi, GoiTap, HoiVien, LuotCheckin, TaiKhoan, ThanhToan, VeLe, YeuCauCheckin


@admin.register(HoiVien)
class HoiVienAdmin(admin.ModelAdmin):
    list_display = ("maHV", "hoTen", "soDienThoai", "ngayTao", "trang_thai")
    search_fields = ("maHV", "hoTen", "soDienThoai")


@admin.register(GoiTap)
class GoiTapAdmin(admin.ModelAdmin):
    list_display = ("maGoi", "tenGoi", "thoiHan", "gia", "thoiHanBaoLuu", "trangThaiBan")


@admin.register(DangKyGoi)
class DangKyGoiAdmin(admin.ModelAdmin):
    list_display = ("maDK", "hoiVien", "goiTap", "loai", "soTien", "ngayBatDau", "ngayKetThuc", "soNgayCongDon")
    list_filter = ("loai", "goiTap")


@admin.register(ThanhToan)
class ThanhToanAdmin(admin.ModelAdmin):
    list_display = ("maGiaoDich", "dangKy", "soTien", "hinhThuc", "thoiGian", "nhanVienThu", "trangThai")
    list_filter = ("hinhThuc", "trangThai")


@admin.register(VeLe)
class VeLeAdmin(admin.ModelAdmin):
    list_display = ("maVe", "giaoDich", "ngayMua", "giaVe", "hoTen", "soDienThoai")


@admin.register(BaoLuu)
class BaoLuuAdmin(admin.ModelAdmin):
    list_display = ("maBL", "dangKy", "ngayBatDau", "ngayKetThuc", "soNgayDaDung", "trangThai")


@admin.register(YeuCauCheckin)
class YeuCauCheckinAdmin(admin.ModelAdmin):
    list_display = ("maYC", "hoiVien", "thoiGianGui", "trangThai")


@admin.register(LuotCheckin)
class LuotCheckinAdmin(admin.ModelAdmin):
    list_display = ("maLuot", "yeuCau", "hoiVien", "thoiGian", "ketQua")


@admin.register(TaiKhoan)
class TaiKhoanAdmin(admin.ModelAdmin):
    list_display = ("tenDangNhap", "email", "soDienThoai")
    exclude = ("password",)
