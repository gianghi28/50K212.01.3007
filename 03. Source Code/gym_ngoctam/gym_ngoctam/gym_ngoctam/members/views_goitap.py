"""UC03 – Quản lý gói tập: danh sách, chi tiết, thêm (3.1), chỉnh sửa (3.2), lịch sử đăng ký (3.3)."""
from datetime import date, datetime, time

from django.contrib.auth.decorators import login_required
from django.db import DatabaseError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms_goitap import GoiTapSuaForm, GoiTapThemForm, LocLichSuForm
from .models import DangKyGoi, GoiTap

MENU = {"menu": "goitap"}


@login_required
def goi_tap_list(request):
    return render(request, "goitap/list.html", {**MENU, "goi_list": GoiTap.objects.all()})


@login_required
def goi_tap_chi_tiet(request, pk):
    goi = get_object_or_404(GoiTap, pk=pk)
    return render(request, "goitap/chi_tiet.html", {
        **MENU,
        "goi": goi,
        "hoi_vien_list": goi.hoi_vien_da_dang_ky(),
        "so_dang_dung": len(goi.hoi_vien_dang_dung()),
    })


@login_required
def goi_tap_them(request):
    ctx = {**MENU, "loi_he_thong": False, "goi_moi": None}
    if request.method == "POST":
        form = GoiTapThemForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            try:
                with transaction.atomic():
                    goi = GoiTap.objects.create(
                        tenGoi=d["tenGoi"], thoiHan=d["thoiHan"],
                        thoiHanBaoLuu=d["thoiHanBaoLuu"], gia=d["gia"],
                        trangThaiBan=GoiTap.TrangThaiBan.DANG_BAN,
                    )
            except DatabaseError:
                ctx["loi_he_thong"] = True
            else:
                return redirect(f"{reverse('goi_tap_them')}?ok={goi.pk}")
    else:
        form = GoiTapThemForm()
        ok = request.GET.get("ok")
        if ok:
            ctx["goi_moi"] = GoiTap.objects.filter(pk=ok).first()
    ctx["form"] = form
    return render(request, "goitap/them.html", ctx)


@login_required
def goi_tap_sua(request, pk):
    goi = get_object_or_404(GoiTap, pk=pk)
    ctx = {**MENU, "goi": goi, "loi_he_thong": False, "hoi_xac_nhan": False,
           "thanh_cong": request.GET.get("ok") == "1"}
    if request.method == "POST":
        form = GoiTapSuaForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            chuyen_sang_ngung = goi.dang_ban and not d["dangBan"]
            if chuyen_sang_ngung and request.POST.get("xac_nhan_ngung") != "1":
                # 5a1: hỏi "Ngừng bán gói này?" trước khi lưu
                ctx["hoi_xac_nhan"] = True
                ctx["so_dang_dung"] = len(goi.hoi_vien_dang_dung())
            else:
                try:
                    with transaction.atomic():
                        goi.gia = d["gia"]
                        goi.trangThaiBan = (GoiTap.TrangThaiBan.DANG_BAN if d["dangBan"]
                                            else GoiTap.TrangThaiBan.NGUNG_BAN)
                        goi.save(update_fields=["gia", "trangThaiBan"])
                except DatabaseError:
                    ctx["loi_he_thong"] = True
                else:
                    return redirect(f"{reverse('goi_tap_sua', args=[goi.pk])}?ok=1")
        dang_ban = request.POST.get("dangBan") == "on"
    else:
        form = GoiTapSuaForm(initial={"gia": f"{int(goi.gia)}", "dangBan": goi.dang_ban})
        dang_ban = goi.dang_ban
    ctx.update(form=form, dang_ban=dang_ban)
    return render(request, "goitap/sua.html", ctx)


def _ten_doi_ung(dk):
    """Với dòng chuyển nhượng: tìm người ở đầu kia (2 dòng được tạo cùng thời điểm)."""
    loai_kia = {DangKyGoi.Loai.CHUYEN_DI: DangKyGoi.Loai.NHAN_CHUYEN,
                DangKyGoi.Loai.NHAN_CHUYEN: DangKyGoi.Loai.CHUYEN_DI}.get(dk.loai)
    if not loai_kia:
        return ""
    kia = (DangKyGoi.objects.select_related("hoiVien")
           .filter(loai=loai_kia, ngayDangKy=dk.ngayDangKy).exclude(pk=dk.pk).first())
    return kia.hoiVien.hoTen if kia else ""


@login_required
def lich_su_dang_ky(request):
    form = LocLichSuForm(request.GET or None)
    ctx = {**MENU, "form": form, "loi_ngay": "", "loi_he_thong": False, "ket_qua": []}
    loai = request.GET.get("loai", "")
    ctx["loai"] = loai if loai in dict(DangKyGoi.Loai.choices) else ""
    ctx["loai_list"] = [("", "Tất cả")] + list(DangKyGoi.Loai.choices)
    nam_nay = date.today().year
    ctx["ngay_opts"] = [f"{i:02d}" for i in range(1, 32)]
    ctx["thang_opts"] = [f"{i:02d}" for i in range(1, 13)]
    ctx["nam_opts"] = [str(y) for y in range(nam_nay, nam_nay - 6, -1)]
    ctx["g"] = request.GET

    try:
        qs = DangKyGoi.objects.select_related("hoiVien", "goiTap").order_by("-ngayDangKy")
        if form.is_bound:
            if not form.is_valid():
                ctx["loi_ngay"] = form.non_field_errors()[0]
                qs = qs.none()
            else:
                d = form.cleaned_data
                q = (d.get("q") or "").strip()
                if q:
                    qs = qs.filter(Q(hoiVien__hoTen__icontains=q) | Q(hoiVien__soDienThoai__icontains=q))
                if d["tu_ngay"]:
                    qs = qs.filter(ngayDangKy__gte=datetime.combine(d["tu_ngay"], time.min))
                if d["den_ngay"]:
                    qs = qs.filter(ngayDangKy__lte=datetime.combine(d["den_ngay"], time.max))
                if d["loai"]:
                    qs = qs.filter(loai=d["loai"])
        ket_qua = list(qs)
        for dk in ket_qua:
            dk.ten_doi_ung = _ten_doi_ung(dk)
        ctx["ket_qua"] = ket_qua
    except DatabaseError:
        ctx["loi_he_thong"] = True
    return render(request, "goitap/lich_su.html", ctx)
