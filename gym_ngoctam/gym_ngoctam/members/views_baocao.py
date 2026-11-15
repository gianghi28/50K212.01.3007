"""UC05 – Báo cáo và thống kê."""
from datetime import date, datetime, time

from django.contrib.auth.decorators import login_required
from django.db import DatabaseError
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from . import nghiep_vu as nv
from .models import DangKyGoi, GoiTap, HoiVien, ThanhToan
from .xlsx import tao_xlsx

MENU = {"menu": "baocao"}
LOI_KHOANG = "Khoảng thời gian không hợp lệ. Vui lòng thử lại"


def _gon(so):
    """2800000 → '2,8tr', 800000 → '800k'."""
    so = int(so or 0)
    if so >= 1_000_000:
        return f"{so / 1_000_000:.1f}".rstrip("0").rstrip(".").replace(".", ",") + "tr"
    if so >= 1000:
        return f"{so // 1000}k"
    return str(so)


def _cot(nhan, gia_tri, hien_thi=None):
    return {"nhan": nhan, "gia_tri": gia_tri, "hien_thi": hien_thi if hien_thi is not None else gia_tri}


def _them_chieu_cao(cot):
    lon = max([c["gia_tri"] for c in cot] + [0])
    for c in cot:
        c["pct"] = round(c["gia_tri"] * 100 / lon) if lon else 0
    return cot


def _thang_trong_nam(g, mac_dinh_tu, mac_dinh_den):
    nam_nay = timezone.now().year
    try:
        nam = int(g.get("nam") or nam_nay)
        tu = int(g.get("tu") or mac_dinh_tu)
        den = int(g.get("den") or mac_dinh_den)
    except ValueError:
        return nam_nay, mac_dinh_tu, mac_dinh_den, True
    return nam, tu, den, tu > den


def _xuat(ten_file, cot_tieu_de, dong, sheet):
    resp = HttpResponse(tao_xlsx(cot_tieu_de, dong, sheet),
                        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = f'attachment; filename="{ten_file}.xlsx"'
    return resp


def _bo_loc_thang():
    nam_nay = timezone.now().year
    return {"nam_opts": list(range(nam_nay, nam_nay - 5, -1)), "thang_opts": list(range(1, 13))}


def _ba_thang_gan_nhat():
    """3 tháng gần nhất tính đến tháng hiện tại, cũ → mới. VD tháng 11/2026 → [(2026,9),(2026,10),(2026,11)]."""
    now = timezone.now()
    y, m, ds = now.year, now.month, []
    for _ in range(3):
        ds.insert(0, (y, m))
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    return ds


def _mac_dinh_bo_loc(thang):
    """Giá trị hiện trên 3 ô Năm/Từ/Đến khi chưa lọc (nếu 3 tháng cùng 1 năm)."""
    if thang[0][0] == thang[-1][0]:
        return thang[0][0], thang[0][1], thang[-1][1]
    return timezone.now().year, None, None


@login_required
def bao_cao_chinh(request):
    return render(request, "baocao/chinh.html", MENU)


# ---------------------------------------------------------------- UC05.1 Doanh thu theo tháng
def _du_lieu_doanh_thu(g):
    now = timezone.now()
    co_loc = bool(g.get("loc"))
    if co_loc:
        nam, tu, den, loi = _thang_trong_nam(g, 1, 12)
        if loi:
            return None, nam, tu, den, True
        thang = [(nam, m) for m in range(tu, den + 1)]
    else:  # mặc định: 3 tháng gần nhất
        thang = _ba_thang_gan_nhat()
        nam, tu, den = _mac_dinh_bo_loc(thang)
    cung_nam = thang[0][0] == thang[-1][0]
    cot = []
    for y, m in thang:
        dau = datetime(y, m, 1)
        cuoi = datetime(y + (m == 12), m % 12 + 1, 1)
        tong = (ThanhToan.objects.filter(trangThai=ThanhToan.TrangThai.THANH_CONG, thoiGian__gte=dau,
                                         thoiGian__lt=min(cuoi, now)).aggregate(s=Sum("soTien"))["s"] or 0)
        nhan = f"T{m}" if cung_nam else f"T{m}/{str(y)[2:]}"
        cot.append(_cot(nhan, int(tong), _gon(tong)))
        cot[-1]["ten_day_du"] = f"Tháng {m}/{y}"
    return cot, nam, tu, den, False


@login_required
def doanh_thu(request):
    ctx = {**MENU, **_bo_loc_thang(), "g": request.GET, "loi_he_thong": False}
    try:
        cot, nam, tu, den, loi = _du_lieu_doanh_thu(request.GET)
    except DatabaseError:
        ctx["loi_he_thong"] = True
        return render(request, "baocao/doanh_thu.html", ctx)
    ctx.update(nam=nam, tu=tu, den=den, loi=LOI_KHOANG if loi else "")
    if not loi:
        tong = sum(c["gia_tri"] for c in cot)
        ctx.update(cot=_them_chieu_cao(cot), tong=nv.vnd(tong), co_du_lieu=tong > 0)
        if tong:
            ctx["cao_nhat"] = max(cot, key=lambda c: c["gia_tri"])
            ctx["thap_nhat"] = min(cot, key=lambda c: c["gia_tri"])
    if request.GET.get("xuat") and not loi:
        return _xuat("doanh_thu_theo_thang", ["Tháng", "Doanh thu (VNĐ)"],
                     [[c["ten_day_du"], c["gia_tri"]] for c in cot], "Doanh thu")
    return render(request, "baocao/doanh_thu.html", ctx)


# ---------------------------------------------------------------- UC05.2 Hội viên mới theo tháng
@login_required
def hoi_vien_moi(request):
    now = timezone.now()
    g = request.GET
    ctx = {**MENU, **_bo_loc_thang(), "g": g, "loi_he_thong": False}
    if g.get("loc"):
        nam, tu, den, loi = _thang_trong_nam(g, 1, 12)
        thang = [(nam, m) for m in range(tu, den + 1)] if not loi else []
    else:  # mặc định: 3 tháng gần nhất
        thang, loi = _ba_thang_gan_nhat(), False
        nam, tu, den = _mac_dinh_bo_loc(thang)
    ctx.update(nam=nam, tu=tu, den=den, loi=LOI_KHOANG if loi else "")
    if not loi:
        cung_nam = thang[0][0] == thang[-1][0]
        try:
            cot = []
            for y, m in thang:
                so = HoiVien.tat_ca.filter(ngayTao__year=y, ngayTao__month=m, ngayTao__lte=now).count()
                c = _cot(f"T{m}" if cung_nam else f"T{m}/{str(y)[2:]}", so)
                c["ten_day_du"] = f"Tháng {m}/{y}"
                cot.append(c)
        except DatabaseError:
            ctx["loi_he_thong"] = True
            return render(request, "baocao/hoi_vien_moi.html", ctx)
        tong = sum(c["gia_tri"] for c in cot)
        ctx.update(cot=_them_chieu_cao(cot), tong=tong)
        if g.get("xuat"):
            return _xuat("hoi_vien_moi_theo_thang", ["Tháng", "Hội viên mới"],
                         [[c["ten_day_du"], c["gia_tri"]] for c in cot] + [["Tổng", tong]], "Hội viên mới")
    return render(request, "baocao/hoi_vien_moi.html", ctx)


# ---------------------------------------------------------------- UC05.3 Hội viên đang tập
@login_required
def dang_tap(request):
    ctx = {**MENU, "loi_he_thong": False}
    try:
        dem = {}
        for hv in HoiVien.objects.all():
            if hv.trang_thai == "Còn hạn" and not hv.da_chuyen_nhuong_het:
                g = hv.dang_ky_hien_tai().goiTap
                dem[g.pk] = dem.get(g.pk, 0) + 1
        goi = list(GoiTap.objects.order_by("thoiHan"))
    except DatabaseError:
        ctx["loi_he_thong"] = True
        return render(request, "baocao/dang_tap.html", ctx)
    tong = sum(dem.values())
    dong = [{"ten": nv.ten_goi(g), "so": dem.get(g.pk, 0)} for g in goi if g.dang_ban or dem.get(g.pk)]
    lon = max([d["so"] for d in dong] + [0])
    for d in dong:
        d["pct"] = round(d["so"] * 100 / lon) if lon else 0
    ctx.update(tong=tong, dong=dong)
    if request.GET.get("xuat"):
        return _xuat("hoi_vien_dang_tap", ["Gói tập", "Số hội viên đang tập"],
                     [[d["ten"], d["so"]] for d in dong] + [["Tổng", tong]], "Đang tập")
    return render(request, "baocao/dang_tap.html", ctx)


# ---------------------------------------------------------------- UC05.4 Số lượng gói tập được đăng ký
def _ngay(g, p):
    d, m, y = (g.get(f"{p}_{k}", "") for k in ("d", "m", "y"))
    if not (d or m or y):
        return None, False
    try:
        return date(int(y), int(m), int(d)), False
    except ValueError:
        return None, True


@login_required
def goi_dang_ky(request):
    now = timezone.now()
    g = request.GET
    ctx = {**MENU, "g": g, "loi_he_thong": False,
           "ngay_opts": [f"{i:02d}" for i in range(1, 32)], "thang_opts2": [f"{i:02d}" for i in range(1, 13)],
           "nam_opts": [str(y) for y in range(now.year, now.year - 6, -1)]}
    tu, l1 = _ngay(g, "tu")
    den, l2 = _ngay(g, "den")
    tu = tu or date(now.year, 1, 1)
    den = den or now.date()
    loi = l1 or l2 or tu > den
    ctx.update(tu=tu, den=den, loi=LOI_KHOANG if loi else "")
    if not loi:
        try:
            qs = DangKyGoi.objects.filter(
                loai__in=[DangKyGoi.Loai.DANG_KY_MOI, DangKyGoi.Loai.GIA_HAN, DangKyGoi.Loai.NANG_CAP],
                ngayDangKy__gte=datetime.combine(tu, time.min), ngayDangKy__lte=datetime.combine(den, time.max))
            cot = []
            for goi in GoiTap.objects.order_by("thoiHan"):
                so = qs.filter(goiTap=goi).count()
                if goi.dang_ban or so:
                    ten = goi.tenGoi.replace("Gói ", "").replace("tháng", "th").replace("năm", "n")
                    c = _cot(ten, so)
                    c["ten_day_du"] = nv.ten_goi(goi)
                    cot.append(c)
        except DatabaseError:
            ctx["loi_he_thong"] = True
            return render(request, "baocao/goi_dang_ky.html", ctx)
        tong = sum(c["gia_tri"] for c in cot)
        ctx.update(cot=_them_chieu_cao(cot), tong=tong)
        if tong:
            ctx["nhieu_nhat"] = max(cot, key=lambda c: c["gia_tri"])
            ctx["it_nhat"] = min(cot, key=lambda c: c["gia_tri"])
        if g.get("xuat"):
            return _xuat("so_luong_goi_dang_ky", ["Gói tập", "Số lượt đăng ký"],
                         [[c["ten_day_du"], c["gia_tri"]] for c in cot] + [["Tổng", tong]], "Gói tập")
    return render(request, "baocao/goi_dang_ky.html", ctx)
