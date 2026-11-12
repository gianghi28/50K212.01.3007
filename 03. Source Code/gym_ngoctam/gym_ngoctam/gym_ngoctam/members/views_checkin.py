"""UC04 – Quản lý check-in: màn chính, xác nhận (04.1), lịch sử (04.2), khách gửi yêu cầu (04.3), vé lẻ (04.4)."""
import re
from datetime import date, datetime, time

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import DatabaseError, transaction
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from . import nghiep_vu as nv
from .models import HoiVien, LuotCheckin, ThanhToan, VeLe, YeuCauCheckin, ket_thuc_bao_luu_het_han
from .xlsx import tao_xlsx

MENU = {"menu": "checkin"}
SDT_RE = re.compile(r"^0\d{9}$")
KEY_VE_LE = "ve_le_cho"
KEY_YC = "yeu_cau_checkin"


def _yc_cho():
    return YeuCauCheckin.objects.select_related("hoiVien").filter(
        trangThai=YeuCauCheckin.TrangThai.CHO_XAC_NHAN, hoiVien__daXoa=False).order_by("thoiGianGui")


# ================================================================== Quản lý
@login_required
def checkin_chinh(request):
    return render(request, "checkin/chinh.html", {**MENU, "so_cho": _yc_cho().count(),
                                                   "yc_dau": _yc_cho().first()})


@login_required
def checkin_so_cho(request):
    return JsonResponse({"so_cho": _yc_cho().count()})


@login_required
def checkin_xac_nhan(request, ma):
    ket_thuc_bao_luu_het_han()
    yc = get_object_or_404(YeuCauCheckin.objects.select_related("hoiVien"), pk=ma)
    if yc.trangThai != YeuCauCheckin.TrangThai.CHO_XAC_NHAN:
        return redirect("checkin_chinh")
    hv = yc.hoiVien
    het_han = hv.trang_thai in ("Hết hạn", "Chưa có gói") or hv.da_chuyen_nhuong_het
    ctx = {**MENU, "yc": yc, "hv": hv, "dk": hv.dang_ky_hien_tai(), "bl": hv.bao_luu_hien_tai(),
           "het_han": het_han, "loi_he_thong": False}

    if request.method == "POST":
        if request.POST.get("huy") == "1" or request.POST.get("dong_loi") == "1":
            if request.POST.get("dong_loi") == "1":
                yc.trangThai = YeuCauCheckin.TrangThai.LOI
            else:
                yc.trangThai = (YeuCauCheckin.TrangThai.HUY_HET_HAN if het_han else YeuCauCheckin.TrangThai.DA_HUY)
            yc.save(update_fields=["trangThai"])
            return redirect("checkin_chinh")
        if not het_han:
            try:
                with transaction.atomic():
                    dang_bl = hv.dang_bao_luu
                    LuotCheckin.objects.create(
                        yeuCau=yc, hoiVien=hv,
                        ketQua=LuotCheckin.KetQua.BAO_LUU_KET_THUC if dang_bl else LuotCheckin.KetQua.THANH_CONG)
                    if dang_bl:  # chỉ kết thúc bảo lưu sau khi lưu lịch sử thành công
                        nv.ket_thuc_bao_luu(hv)
                    yc.trangThai = YeuCauCheckin.TrangThai.DA_XAC_NHAN
                    yc.save(update_fields=["trangThai"])
            except DatabaseError:
                ctx["loi_he_thong"] = True
            else:
                messages.success(request, "Check-in thành công")
                return redirect("checkin_chinh")
    return render(request, "checkin/xac_nhan.html", ctx)


# ---------------------------------------------------------------- Lịch sử check-in (UC04.2)
def _doc_ngay(g, prefix):
    d, m, y = (g.get(f"{prefix}_{k}", "") for k in ("d", "m", "y"))
    if not (d or m or y):
        return None, False
    try:
        return date(int(y), int(m), int(d)), False
    except (TypeError, ValueError):
        return None, True


def _loc_lich_su(g):
    """Trả về (queryset, tu, den, loi). Mặc định: hôm nay."""
    hom_nay = timezone.now().date()
    tu, loi1 = _doc_ngay(g, "tu")
    den, loi2 = _doc_ngay(g, "den")
    loi = loi1 or loi2 or bool((tu and den and tu > den) or (den and den > hom_nay) or (tu and tu > hom_nay))
    if not g.get("loc"):
        tu = den = hom_nay
    tu = tu or date(2000, 1, 1)
    den = den or hom_nay
    qs = LuotCheckin.objects.select_related("hoiVien").filter(
        thoiGian__gte=datetime.combine(tu, time.min), thoiGian__lte=datetime.combine(den, time.max)
    ).order_by("-thoiGian")
    q = (g.get("q") or "").strip()
    if q:
        qs = qs.filter(Q(hoiVien__hoTen__icontains=q) | Q(hoiVien__soDienThoai__icontains=q))
    return qs, tu, den, loi


def _ten_goi_luc(luot):
    dk = (luot.hoiVien.cac_dang_ky.filter(ngayBatDau__lte=luot.thoiGian)
          .exclude(loai="Chuyển nhượng đi").order_by("-ngayKetThuc").first())
    return nv.ten_goi(dk.goiTap) if dk else "Chưa có gói"


@login_required
def checkin_lich_su(request):
    try:
        qs, tu, den, loi = _loc_lich_su(request.GET)
        if loi:
            return redirect(f"{reverse('checkin_loc')}?{request.GET.urlencode()}&loi=1")
        ds = list(qs)
        for l in ds:
            l.ten_goi = _ten_goi_luc(l)
    except DatabaseError:
        return render(request, "checkin/lich_su.html", {**MENU, "loi_he_thong": True, "ds": []})
    return render(request, "checkin/lich_su.html", {
        **MENU, "ds": ds, "tu": tu, "den": den, "qs": request.GET.urlencode(), "loi_he_thong": False})


@login_required
def checkin_loc(request):
    nam_nay = date.today().year
    g = request.GET.copy()
    g.pop("loi", None)
    return render(request, "checkin/loc.html", {
        **MENU, "g": request.GET, "loi": request.GET.get("loi") == "1", "qs_back": "" if request.GET.get("loi") else g.urlencode(),
        "ngay_opts": [f"{i:02d}" for i in range(1, 32)], "thang_opts": [f"{i:02d}" for i in range(1, 13)],
        "nam_opts": [str(y) for y in range(nam_nay, nam_nay - 6, -1)]})


@login_required
def checkin_xuat_excel(request):
    qs, tu, den, loi = _loc_lich_su(request.GET)
    dong = []
    for l in qs:
        dong.append([l.hoiVien.hoTen, l.hoiVien.maHV, l.hoiVien.soDienThoai, _ten_goi_luc(l),
                     l.thoiGian.strftime("%H:%M"), l.thoiGian.strftime("%d/%m/%Y")])
    data = tao_xlsx(["Họ tên", "Mã HV", "SĐT", "Gói tập", "Giờ", "Ngày"], dong, "Lịch sử check-in")
    resp = HttpResponse(data, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = f'attachment; filename="lich_su_checkin_{tu:%Y%m%d}_{den:%Y%m%d}.xlsx"'
    return resp


# ---------------------------------------------------------------- Bán vé lẻ (UC04.4)
@login_required
def ve_le(request):
    ctx = {**MENU, "gia": nv.vnd(VeLe.GIA_MAC_DINH), "loi_sdt": "", "hinh_thuc": "qr",
           "hoTen": "", "sdt": ""}
    if request.method == "POST":
        ho_ten = " ".join(request.POST.get("hoTen", "").split())
        sdt = request.POST.get("sdt", "").strip().replace(" ", "")
        hinh_thuc = "tienmat" if request.POST.get("hinh_thuc") == "tienmat" else "qr"
        ctx.update(hoTen=ho_ten, sdt=sdt, hinh_thuc=hinh_thuc)
        if sdt and not SDT_RE.match(sdt):
            ctx["loi_sdt"] = "Số điện thoại không hợp lệ. Vui lòng nhập 10 chữ số, bắt đầu bằng số 0."
        else:
            request.session[KEY_VE_LE] = {"hoTen": ho_ten, "sdt": sdt, "hinh_thuc": hinh_thuc}
            return redirect("ve_le_thanh_toan")
    return render(request, "checkin/ve_le.html", ctx)


@login_required
def ve_le_thanh_toan(request):
    cho = request.session.get(KEY_VE_LE)
    if not cho:
        return redirect("checkin_chinh")
    tien_mat = cho["hinh_thuc"] == "tienmat"
    ctx = {**MENU, "cho": cho, "tien_mat": tien_mat, "gia": nv.vnd(VeLe.GIA_MAC_DINH), "loi_he_thong": False,
           "link_qr": "https://api.qrserver.com/v1/create-qr-code/?size=240x240&margin=0&data=VE%20LE%2040000VND"}
    if request.method == "POST":
        if request.POST.get("huy") == "1":
            del request.session[KEY_VE_LE]
            return redirect("checkin_chinh")
        try:
            with transaction.atomic():
                gd = ThanhToan.objects.create(
                    soTien=VeLe.GIA_MAC_DINH, nhanVienThu=request.user.get_username(),
                    hinhThuc=ThanhToan.HinhThuc.TIEN_MAT if tien_mat else ThanhToan.HinhThuc.CHUYEN_KHOAN,
                    trangThai=ThanhToan.TrangThai.THANH_CONG)
                ve = VeLe.objects.create(giaoDich=gd, giaVe=VeLe.GIA_MAC_DINH,
                                         hoTen=cho["hoTen"] or None, soDienThoai=cho["sdt"] or None)
        except DatabaseError:
            ctx["loi_he_thong"] = True
        else:
            del request.session[KEY_VE_LE]
            return redirect("ve_le_xong", ma=ve.pk)
    return render(request, "checkin/ve_le_thanh_toan.html", ctx)


@login_required
def ve_le_xong(request, ma):
    ve = get_object_or_404(VeLe.objects.select_related("giaoDich"), pk=ma)
    return render(request, "checkin/ve_le_xong.html", {**MENU, "ve": ve, "gia": nv.vnd(ve.giaVe)})


# ================================================================== Màn hình khách (UC04.3) – không cần đăng nhập
def khach_checkin(request):
    yc_id = request.session.get(KEY_YC)
    if yc_id and YeuCauCheckin.objects.filter(pk=yc_id).exists():
        return redirect("khach_ket_qua")
    ctx = {"sdt": "", "loi": ""}
    if request.method == "POST":
        sdt = request.POST.get("sdt", "").strip().replace(" ", "")
        ctx["sdt"] = sdt
        if not SDT_RE.match(sdt):
            ctx["loi"] = "Số điện thoại không hợp lệ"
        else:
            hv = HoiVien.objects.filter(soDienThoai=sdt).first()
            if hv is None:
                ctx["loi"] = "Không tìm thấy hội viên với số điện thoại này. Vui lòng nhập lại."
            else:
                try:
                    yc = YeuCauCheckin.objects.create(hoiVien=hv)
                except DatabaseError:
                    ctx["loi_he_thong"] = True
                else:
                    request.session[KEY_YC] = yc.pk
                    return redirect("khach_ket_qua")
    return render(request, "checkin/khach_nhap_sdt.html", ctx)


def _ket_qua_khach(yc):
    hv = yc.hoiVien
    dk = hv.dang_ky_hien_tai()
    d = {"trang_thai_yc": yc.trangThai, "sdt": hv.soDienThoai, "gio_gui": yc.thoiGianGui.strftime("%H:%M"),
         "ho_ten": hv.hoTen, "goi": nv.ten_goi(dk.goiTap) if dk else "Chưa có gói",
         "so_ngay": hv.so_ngay_con_lai, "tt_goi": hv.trang_thai}
    luot = yc.cac_luot.first()
    if luot:
        d["gio_checkin"] = luot.thoiGian.strftime("%H:%M")
        d["bao_luu_ket_thuc"] = luot.ketQua == LuotCheckin.KetQua.BAO_LUU_KET_THUC
    return d


def khach_ket_qua(request):
    yc_id = request.session.get(KEY_YC)
    yc = YeuCauCheckin.objects.select_related("hoiVien").filter(pk=yc_id).first() if yc_id else None
    if yc is None:
        return redirect("khach_checkin")
    if request.method == "POST":
        if yc.trangThai == YeuCauCheckin.TrangThai.CHO_XAC_NHAN:  # 2a: khách hủy yêu cầu
            yc.trangThai = YeuCauCheckin.TrangThai.KHACH_HUY
            yc.save(update_fields=["trangThai"])
        request.session.pop(KEY_YC, None)
        return redirect("khach_checkin")
    return render(request, "checkin/khach_ket_qua.html", {"yc": yc, "kq": _ket_qua_khach(yc)})


def khach_trang_thai(request):
    yc_id = request.session.get(KEY_YC)
    yc = YeuCauCheckin.objects.filter(pk=yc_id).first() if yc_id else None
    return JsonResponse({"trang_thai": yc.trangThai if yc else ""})
