"""Quy tắc nghiệp vụ UC02.5 (Đăng ký gói), UC02.6 (Bảo lưu), UC02.7 (Thanh toán)."""
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import BaoLuu, DangKyGoi, GoiTap, HoiVien, ThanhToan


def ten_goi(goi):
    ten = goi.tenGoi.strip()
    return ten if ten.lower().startswith("gói") else f"Gói {ten}"


def vnd(so):
    return f"{int(so):,}".replace(",", ".")


def tinh_dang_ky(hv, goi):
    """Tính loại giao dịch, ngày bắt đầu/kết thúc, số ngày cộng dồn khi chọn gói `goi` cho hội viên `hv`
    (hv = None khi đang thêm hội viên mới). Theo business rules UC02.5."""
    now = timezone.now()
    dk_ht = hv.dang_ky_hien_tai() if hv else None
    con_lai = hv.so_ngay_con_lai if hv else 0

    if dk_ht is None or con_lai <= 0:
        loai, tieu_de = DangKyGoi.Loai.DANG_KY_MOI, "Đăng ký gói"
        cong_don = 0
        ngay_ket_thuc = now + timedelta(days=goi.thoiHan)
        so_ngay_text = f"{goi.thoiHan} ngày (bắt đầu từ hôm nay)"
    else:
        cong_don = con_lai
        ngay_ket_thuc = now + timedelta(days=goi.thoiHan + con_lai)
        tong = goi.thoiHan + con_lai
        so_ngay_text = f"{con_lai} + {goi.thoiHan} = {tong} ngày"
        if dk_ht.goiTap_id == goi.pk:
            loai, tieu_de = DangKyGoi.Loai.GIA_HAN, "Gia hạn"
        else:
            loai = DangKyGoi.Loai.NANG_CAP
            tieu_de = ("Nâng cấp (gói thời hạn dài hơn)" if goi.thoiHan >= dk_ht.goiTap.thoiHan
                       else "Đổi gói (gói thời hạn ngắn hơn)")

    if dk_ht is None:
        goi_ht_text = "Chưa có gói"
    elif con_lai <= 0:
        goi_ht_text = f"{ten_goi(dk_ht.goiTap)} · Hết hạn (0 ngày)"
    else:
        goi_ht_text = f"{ten_goi(dk_ht.goiTap)} · còn {con_lai} ngày"

    return {
        "loai": loai, "tieu_de": tieu_de, "cong_don": cong_don,
        "ngay_bat_dau": now, "ngay_ket_thuc": ngay_ket_thuc,
        "goi_ht_text": goi_ht_text,
        "goi_moi_text": f"{ten_goi(goi)} · {goi.thoiHan} ngày",
        "so_ngay_text": so_ngay_text,
        "so_tien": goi.gia,
    }


@transaction.atomic
def ghi_nhan_dang_ky(hv, goi, hinh_thuc, nhan_vien):
    """Sau khi thanh toán thành công: tạo dòng DangKyGoi + ThanhToan."""
    t = tinh_dang_ky(hv, goi)
    dk = DangKyGoi.objects.create(
        hoiVien=hv, goiTap=goi, loai=t["loai"], soTien=goi.gia,
        ngayDangKy=t["ngay_bat_dau"], ngayBatDau=t["ngay_bat_dau"],
        ngayKetThuc=t["ngay_ket_thuc"], soNgayCongDon=t["cong_don"],
    )
    tt = ThanhToan.objects.create(
        dangKy=dk, soTien=goi.gia, hinhThuc=hinh_thuc, nhanVienThu=nhan_vien,
        trangThai=ThanhToan.TrangThai.THANH_CONG,
    )
    return dk, tt


# ------------------------------------------------------------------ Bảo lưu (UC02.6)
def kiem_tra_bao_luu(hv):
    """Trả về câu báo lỗi nếu không được bảo lưu, None nếu được."""
    if hv.trang_thai in ("Hết hạn", "Chưa có gói"):
        return "Gói tập đã hết hạn, không thể bảo lưu"
    if hv.da_dung_quyen_bao_luu:
        return "Gói tập đã sử dụng quyền bảo lưu, không thể bảo lưu thêm"
    return None


@transaction.atomic
def bat_dau_bao_luu(hv):
    dk = hv.dang_ky_hien_tai()
    so_ngay = dk.goiTap.thoiHanBaoLuu or 0
    now = timezone.now()
    BaoLuu.objects.create(dangKy=dk, ngayBatDau=now, ngayKetThuc=now + timedelta(days=so_ngay),
                          soNgayDaDung=0, trangThai=BaoLuu.TrangThai.DANG_BAO_LUU)
    # Ngày hết hạn gói được dời thêm đúng số ngày bảo lưu
    dk.ngayKetThuc = dk.ngayKetThuc + timedelta(days=so_ngay)
    dk.save(update_fields=["ngayKetThuc"])


def thong_tin_ket_thuc_som(hv):
    """Số ngày bảo lưu đã dùng và ngày kết thúc mới nếu kết thúc bảo lưu hôm nay."""
    bl = hv.bao_luu_hien_tai()
    dk = bl.dangKy
    da_dung = max((timezone.now().date() - bl.ngayBatDau.date()).days, 0)
    ket_thuc_goc = dk.ngayKetThuc - (bl.ngayKetThuc - bl.ngayBatDau)
    return da_dung, ket_thuc_goc + timedelta(days=da_dung)


@transaction.atomic
def ket_thuc_bao_luu(hv):
    """Kết thúc bảo lưu sớm (bỏ tick hoặc check-in): ngày hết hạn = gốc + số ngày thực tế đã bảo lưu."""
    bl = hv.bao_luu_hien_tai()
    if bl is None:
        return
    da_dung, ket_thuc_moi = thong_tin_ket_thuc_som(hv)
    dk = bl.dangKy
    dk.ngayKetThuc = ket_thuc_moi
    dk.save(update_fields=["ngayKetThuc"])
    bl.ngayKetThuc = timezone.now()
    bl.soNgayDaDung = da_dung
    bl.trangThai = BaoLuu.TrangThai.DA_KET_THUC
    bl.save(update_fields=["ngayKetThuc", "soNgayDaDung", "trangThai"])


def goi_dang_ban():
    return GoiTap.objects.filter(trangThaiBan=GoiTap.TrangThaiBan.DANG_BAN).order_by("thoiHan")


def ma_hv_tiep_theo():
    from .models import ma_tiep_theo
    return ma_tiep_theo(HoiVien, "HV")


# ------------------------------------------------------------------ Xóa hội viên (UC02.3)
SO_NGAY_KHONG_HOAT_DONG = 150  # ~5 tháng


def ngay_hoat_dong_gan_nhat(hv):
    """Mốc gần nhất trong: lần check-in cuối, lần thanh toán gói cuối, ngày hết hạn gói gần nhất."""
    from .models import LuotCheckin
    moc = [hv.ngayTao]
    lc = LuotCheckin.objects.filter(hoiVien=hv).order_by("-thoiGian").first()
    if lc:
        moc.append(lc.thoiGian)
    tt = ThanhToan.objects.filter(dangKy__hoiVien=hv).order_by("-thoiGian").first()
    if tt:
        moc.append(tt.thoiGian)
    dk = hv.cac_dang_ky.order_by("-ngayKetThuc").first()
    if dk:
        moc.append(dk.ngayKetThuc)
    return max(moc)


@transaction.atomic
def xoa_mem(ds_hoi_vien):
    so = 0
    for hv in ds_hoi_vien:
        hv.daXoa = True
        hv.save(update_fields=["daXoa"])
        so += 1
    return so


def don_dep_hoi_vien_khong_hoat_dong():
    """TH2: tự xóa mềm hội viên không còn hạn, không bảo lưu và không hoạt động quá 5 tháng.
    Trả về danh sách mã đã xóa (ghi nhật ký)."""
    import logging
    log = logging.getLogger("gym")
    moc = timezone.now() - timedelta(days=SO_NGAY_KHONG_HOAT_DONG)
    can_xoa = [hv for hv in HoiVien.objects.all()
               if hv.trang_thai not in ("Còn hạn", "Đang bảo lưu") and ngay_hoat_dong_gan_nhat(hv) < moc]
    try:
        xoa_mem(can_xoa)
    except Exception:  # 1b: lỗi thì không xóa, thử lại lần quét sau
        log.exception("Dọn dẹp hội viên lỗi")
        return []
    if can_xoa:
        log.info("Tự động xóa %d hội viên: %s", len(can_xoa), ", ".join(h.pk for h in can_xoa))
    return [h.pk for h in can_xoa]


# ------------------------------------------------------------------ Chuyển nhượng (UC02.8)
def kiem_tra_nguoi_chuyen(hv):
    if hv.dang_bao_luu:
        return "Hội viên đang bảo lưu, không thể chuyển nhượng gói tập"
    if hv.trang_thai != "Còn hạn" or hv.da_chuyen_nhuong_het:
        return "Gói tập đã hết hạn, không thể chuyển nhượng"
    return None


def tinh_chuyen_nhuong(nguoi_chuyen, nguoi_nhan):
    now = timezone.now()
    dk_chuyen = nguoi_chuyen.dang_ky_hien_tai()
    y = nguoi_chuyen.so_ngay_con_lai
    if nguoi_nhan.trang_thai == "Còn hạn" and not nguoi_nhan.da_chuyen_nhuong_het:
        dk_nhan = nguoi_nhan.dang_ky_hien_tai()
        x = nguoi_nhan.so_ngay_con_lai
        return {"con_han": True, "goi_chuyen": dk_chuyen.goiTap, "goi_nhan": dk_nhan.goiTap,
                "x": x, "y": y, "tong": x + y, "ket_thuc": dk_nhan.ngayKetThuc + timedelta(days=y), "now": now}
    return {"con_han": False, "goi_chuyen": dk_chuyen.goiTap, "goi_nhan": dk_chuyen.goiTap,
            "x": 0, "y": y, "tong": y, "ket_thuc": now + timedelta(days=y), "now": now}


@transaction.atomic
def thuc_hien_chuyen_nhuong(nguoi_chuyen, nguoi_nhan):
    t = tinh_chuyen_nhuong(nguoi_chuyen, nguoi_nhan)
    now = t["now"]
    dk_cu = nguoi_chuyen.dang_ky_hien_tai()
    dk_cu.ngayKetThuc = max(now, dk_cu.ngayBatDau)  # người chuyển hết gói từ thời điểm này
    dk_cu.save(update_fields=["ngayKetThuc"])
    # 2 dòng lịch sử cùng thời điểm (để màn Lịch sử đăng ký ghép được người chuyển ↔ người nhận)
    DangKyGoi.objects.create(hoiVien=nguoi_chuyen, goiTap=t["goi_chuyen"], loai=DangKyGoi.Loai.CHUYEN_DI,
                             soTien=0, ngayDangKy=now, ngayBatDau=now, ngayKetThuc=now, soNgayCongDon=t["y"])
    DangKyGoi.objects.create(hoiVien=nguoi_nhan, goiTap=t["goi_nhan"], loai=DangKyGoi.Loai.NHAN_CHUYEN,
                             soTien=0, ngayDangKy=now, ngayBatDau=now, ngayKetThuc=t["ket_thuc"],
                             soNgayCongDon=t["y"])
    return t
