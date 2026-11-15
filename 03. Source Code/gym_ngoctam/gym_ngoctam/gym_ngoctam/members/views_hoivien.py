"""UC02 – Quản lý hội viên: danh sách, chi tiết, thêm (02.1), chỉnh sửa (02.2 + 02.5 + 02.6), thanh toán (02.7)."""
import os
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import File
from django.core.files.storage import default_storage
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from . import nghiep_vu as nv
from .forms_hoivien import HoiVienSuaForm, HoiVienThemForm
from .models import GoiTap, HoiVien, ThanhToan, ket_thuc_bao_luu_het_han, ma_tiep_theo

MENU = {"menu": "hoivien"}
SESSION_KEY = "cho_thanh_toan"


def _goi_json(hv=None):
    """Dữ liệu các gói đang bán cho bảng chọn gói (JS dùng để tính khung Đăng ký gói)."""
    ds = []
    for g in nv.goi_dang_ban():
        item = {"ma": g.pk, "ten": nv.ten_goi(g), "gia": nv.vnd(g.gia), "thoiHan": g.thoiHan}
        if hv is not None:
            t = nv.tinh_dang_ky(hv, g)
            item.update(tieuDe=t["tieu_de"], goiHT=t["goi_ht_text"], goiMoi=t["goi_moi_text"],
                        soNgay=t["so_ngay_text"])
        ds.append(item)
    return ds


# ------------------------------------------------------------------ Danh sách
@login_required
def hoi_vien_list(request):
    ket_thuc_bao_luu_het_han()
    nv.don_dep_hoi_vien_khong_hoat_dong()
    q = request.GET.get("q", "").strip()
    qs = HoiVien.objects.all()
    if q:
        qs = qs.filter(Q(hoTen__icontains=q) | Q(soDienThoai__icontains=q) | Q(maHV__icontains=q))
    return render(request, "hoivien/list.html", {**MENU, "ds": list(qs), "q": q,
                                                  "tong": HoiVien.objects.count()})


# ------------------------------------------------------------------ Chi tiết
@login_required
def hoi_vien_chi_tiet(request, pk):
    ket_thuc_bao_luu_het_han()
    hv = get_object_or_404(HoiVien, pk=pk)
    return render(request, "hoivien/chi_tiet.html", {
        **MENU, "hv": hv, "dk": hv.dang_ky_hien_tai(), "bl": hv.bao_luu_hien_tai(),
        "loi_cn": nv.kiem_tra_nguoi_chuyen(hv) if request.GET.get("loi_cn") else "",
    })


# ------------------------------------------------------------------ Thêm (UC02.1)
@login_required
def hoi_vien_them(request):
    ctx = {**MENU, "ma_moi": nv.ma_hv_tiep_theo(), "goi_list": _goi_json(), "anh_tam": "",
           "hv_moi": None}
    if request.method == "POST":
        form = HoiVienThemForm(request.POST, files=request.FILES)
        if form.is_valid():
            d = form.cleaned_data
            request.session[SESSION_KEY] = {
                "kieu": "them", "hoTen": d["hoTen"], "soDienThoai": d["soDienThoai"],
                "maGoi": d["maGoi"].pk, "anh_tam": d["anh_tam"],
            }
            return redirect("thanh_toan")
        ctx["anh_tam"] = form.cleaned_data.get("anh_tam") or os.path.basename(request.POST.get("anh_tam", ""))
        ctx["goi_chon"] = GoiTap.objects.filter(pk=request.POST.get("maGoi") or None).first()
    else:
        form = HoiVienThemForm()
        ok = request.GET.get("ok")
        if ok:
            ctx["hv_moi"] = HoiVien.objects.filter(pk=ok).first()
    ctx["form"] = form
    return render(request, "hoivien/them.html", ctx)


# ------------------------------------------------------------------ Chỉnh sửa (UC02.2)
@login_required
def hoi_vien_sua(request, pk):
    ket_thuc_bao_luu_het_han()
    hv = get_object_or_404(HoiVien, pk=pk)
    dang_bao_luu = hv.dang_bao_luu
    ctx = {**MENU, "hv": hv, "dk": hv.dang_ky_hien_tai(), "dang_bao_luu": dang_bao_luu,
           "goi_list": _goi_json(hv), "loi_bao_luu": "", "loi_he_thong": False,
           "thanh_cong": request.GET.get("ok") == "1", "goi_chon": None}
    ctx["bao_luu_so_ngay"] = (ctx["dk"].goiTap.thoiHanBaoLuu or 0) if ctx["dk"] else 0
    ctx["bao_luu_den"] = timezone.now() + timedelta(days=ctx["bao_luu_so_ngay"])
    ctx["loi_dieu_kien_bao_luu"] = nv.kiem_tra_bao_luu(hv) or ""
    if dang_bao_luu:
        ctx["bl"] = hv.bao_luu_hien_tai()
        ctx["da_dung"], ctx["ket_thuc_moi"] = nv.thong_tin_ket_thuc_som(hv)

    if request.method == "POST":
        form = HoiVienSuaForm(request.POST, hoi_vien=hv)
        tick = request.POST.get("baoLuu") == "on"
        if form.is_valid():
            d = form.cleaned_data
            goi = d["maGoi"]
            if goi and dang_bao_luu:
                ctx["loi_bao_luu"] = "Hội viên đang bảo lưu, không thể đăng ký gói tập"
            elif goi and tick:
                ctx["loi_bao_luu"] = "Không thể vừa đổi gói vừa bảo lưu trong cùng một lần cập nhật"
            elif tick and not dang_bao_luu and ctx["loi_dieu_kien_bao_luu"]:
                ctx["loi_bao_luu"] = ctx["loi_dieu_kien_bao_luu"]
            elif goi:
                # 5a: chọn gói → sang Thanh toán, chỉ lưu sau khi thanh toán thành công
                request.session[SESSION_KEY] = {
                    "kieu": "sua", "maHV": hv.pk, "hoTen": d["hoTen"],
                    "soDienThoai": d["soDienThoai"], "maGoi": goi.pk,
                }
                return redirect("thanh_toan")
            else:
                try:
                    with transaction.atomic():
                        hv.hoTen, hv.soDienThoai = d["hoTen"], d["soDienThoai"]
                        hv.save(update_fields=["hoTen", "soDienThoai"])
                        if tick and not dang_bao_luu:
                            nv.bat_dau_bao_luu(hv)
                        elif not tick and dang_bao_luu:
                            nv.ket_thuc_bao_luu(hv)
                except (DatabaseError, IntegrityError):
                    ctx["loi_he_thong"] = True
                else:
                    return redirect(f"{reverse('hoi_vien_sua', args=[hv.pk])}?ok=1")
        ctx["tick"] = tick
        ctx["goi_chon"] = GoiTap.objects.filter(pk=request.POST.get("maGoi") or None).first()
    else:
        form = HoiVienSuaForm(initial={"hoTen": hv.hoTen, "soDienThoai": hv.soDienThoai}, hoi_vien=hv)
        ctx["tick"] = dang_bao_luu
    if ctx["goi_chon"]:
        ctx["dk_moi"] = nv.tinh_dang_ky(hv, ctx["goi_chon"])
    ctx["form"] = form
    return render(request, "hoivien/sua.html", ctx)


# ------------------------------------------------------------------ Thanh toán (UC02.7)
def _chuyen_anh(token, ma_hv):
    """Chuyển ảnh tạm thành ảnh chính thức anh_hoi_vien/HVxxx.ext."""
    if not token:
        return None
    src = f"tam/{token}"
    if not default_storage.exists(src):
        return None
    ext = os.path.splitext(token)[1]
    with default_storage.open(src, "rb") as f:
        ten = default_storage.save(f"anh_hoi_vien/{ma_hv}{ext}", File(f))
    default_storage.delete(src)
    return ten


@login_required
def thanh_toan(request):
    cho = request.session.get(SESSION_KEY)
    if not cho:
        return redirect("hoi_vien_list")
    goi = get_object_or_404(GoiTap, pk=cho["maGoi"])
    hv = HoiVien.objects.filter(pk=cho.get("maHV")).first() if cho["kieu"] == "sua" else None
    tien_mat = request.GET.get("pt") == "tienmat" or request.POST.get("pt") == "tienmat"
    ma_hv = hv.pk if hv else nv.ma_hv_tiep_theo()
    ctx = {**MENU, "cho": cho, "goi": goi, "ten_goi": nv.ten_goi(goi), "so_tien": nv.vnd(goi.gia),
           "ma_hv": ma_hv, "tien_mat": tien_mat, "loi_he_thong": False,
           "ma_gd": ma_tiep_theo(ThanhToan, "GD"), "bay_gio": timezone.now(),
           "nhan_vien": request.user.get_username()}
    ctx["noi_dung_ck"] = f"{ma_hv} {nv.ten_goi(goi)}"
    ctx["link_qr"] = ("https://api.qrserver.com/v1/create-qr-code/?size=240x240&margin=0&data="
                      + f"{ma_hv} {goi.tenGoi} {int(goi.gia)}VND".replace(" ", "%20"))

    if request.method == "POST":
        if request.POST.get("huy") == "1":
            del request.session[SESSION_KEY]
            if cho["kieu"] == "them":
                messages.info(request, "Đã hủy thanh toán. Hội viên chưa được thêm.")
                return redirect("hoi_vien_them")
            messages.info(request, f"Đã hủy đăng ký gói {nv.ten_goi(goi).removeprefix('Gói ')}")
            return redirect("hoi_vien_sua", pk=cho["maHV"])

        hinh_thuc = ThanhToan.HinhThuc.TIEN_MAT if tien_mat else ThanhToan.HinhThuc.CHUYEN_KHOAN
        try:
            with transaction.atomic():
                if cho["kieu"] == "them":
                    hv = HoiVien.objects.create(hoTen=cho["hoTen"], soDienThoai=cho["soDienThoai"])
                    anh = _chuyen_anh(cho.get("anh_tam"), hv.pk)
                    if anh:
                        hv.anhDaiDien.name = anh
                        hv.save(update_fields=["anhDaiDien"])
                else:
                    hv.hoTen, hv.soDienThoai = cho["hoTen"], cho["soDienThoai"]
                    hv.save(update_fields=["hoTen", "soDienThoai"])
                nv.ghi_nhan_dang_ky(hv, goi, hinh_thuc, ctx["nhan_vien"])
        except (DatabaseError, IntegrityError, OSError):
            ctx["loi_he_thong"] = True
        else:
            del request.session[SESSION_KEY]
            if cho["kieu"] == "them":
                return redirect(f"{reverse('hoi_vien_them')}?ok={hv.pk}")
            messages.success(request, "Đăng ký gói tập thành công")
            return redirect("hoi_vien_chi_tiet", pk=hv.pk)

    ctx["hv"] = hv
    return render(request, "hoivien/thanh_toan.html", ctx)



# ------------------------------------------------------------------ Tìm kiếm gợi ý (UC02.4 – 2a)
@login_required
def goi_y_hoi_vien(request):
    q = request.GET.get("q", "").strip()
    if len(q) < 3:
        return JsonResponse({"ket_qua": []})
    ds = HoiVien.objects.filter(Q(hoTen__icontains=q) | Q(soDienThoai__icontains=q) | Q(maHV__icontains=q))[:6]
    ket_qua = []
    for hv in ds:
        dk = hv.dang_ky_hien_tai()
        ket_qua.append({
            "ma": hv.pk, "ten": hv.hoTen, "trangThai": hv.trang_thai,
            "goi": "Không còn gói tập" if hv.da_chuyen_nhuong_het else (nv.ten_goi(dk.goiTap) if dk else "Chưa có gói"),
            "anh": hv.anhDaiDien.url if hv.anhDaiDien else "",
            "link": reverse("hoi_vien_chi_tiet", args=[hv.pk]),
        })
    return JsonResponse({"ket_qua": ket_qua})


# ------------------------------------------------------------------ Xóa hội viên (UC02.3)
@login_required
def hoi_vien_xoa(request):
    ctx = {**MENU, "ds": list(HoiVien.objects.all()), "loi_he_thong": False, "da_xoa": 0, "chon": []}
    if request.method == "POST":
        ma_list = request.POST.getlist("chon")
        ds = list(HoiVien.objects.filter(pk__in=ma_list))
        if ds:
            try:
                so = nv.xoa_mem(ds)
            except DatabaseError:
                ctx["loi_he_thong"] = True
                ctx["chon"] = ma_list
            else:
                return redirect(f"{reverse('hoi_vien_xoa')}?ok={so}")
    else:
        ctx["da_xoa"] = int(request.GET.get("ok", "0") or 0)
    return render(request, "hoivien/xoa.html", ctx)


# ------------------------------------------------------------------ Chuyển nhượng (UC02.8)
@login_required
def chuyen_nhuong(request, pk):
    nguoi_chuyen = get_object_or_404(HoiVien, pk=pk)
    loi = nv.kiem_tra_nguoi_chuyen(nguoi_chuyen)
    if loi:  # 2a / 2b: báo lỗi ngay trên màn Chi tiết hội viên
        return redirect(f"{reverse('hoi_vien_chi_tiet', args=[pk])}?loi_cn=1")
    dk = nguoi_chuyen.dang_ky_hien_tai()
    ctx = {**MENU, "nc": nguoi_chuyen, "dk": dk, "loi_nhan": "", "loi_he_thong": False}

    ma_nhan = request.POST.get("nguoi_nhan") or request.GET.get("nguoi_nhan")
    nguoi_nhan = HoiVien.objects.filter(pk=ma_nhan).exclude(pk=pk).first() if ma_nhan else None

    if nguoi_nhan and nguoi_nhan.dang_bao_luu:
        ctx["loi_nhan"] = "Người nhận đang bảo lưu, không thể nhận chuyển nhượng"
        nguoi_nhan = None

    if nguoi_nhan and request.method == "POST" and request.POST.get("xac_nhan") == "1":
        try:
            nv.thuc_hien_chuyen_nhuong(nguoi_chuyen, nguoi_nhan)
        except DatabaseError:
            ctx["loi_he_thong"] = True
        else:
            messages.success(request, "Chuyển nhượng gói tập thành công")
            return redirect("hoi_vien_chi_tiet", pk=pk)

    if nguoi_nhan:  # bước 7: màn xác nhận
        ctx.update(nn=nguoi_nhan, t=nv.tinh_chuyen_nhuong(nguoi_chuyen, nguoi_nhan))
        return render(request, "hoivien/chuyen_nhuong_xac_nhan.html", ctx)

    ctx["ds"] = list(HoiVien.objects.exclude(pk=pk))
    return render(request, "hoivien/chuyen_nhuong.html", ctx)
