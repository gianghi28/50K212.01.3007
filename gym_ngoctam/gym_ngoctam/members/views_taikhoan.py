"""UC01 – Đăng nhập + Quên mật khẩu (mã xác minh 6 số, hiệu lực 5 phút, gửi lại sau 60 giây)."""
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.core.mail import send_mail
from django.db import DatabaseError
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from .models import TaiKhoan

log = logging.getLogger("gym")
KEY = "quen_mk"
HIEU_LUC = timedelta(minutes=5)
GUI_LAI_SAU = 60  # giây


def dang_nhap(request):
    if request.user.is_authenticated:
        return redirect("hoi_vien_list")
    ctx = {"ten": "", "loi_ten": "", "loi_mk": "", "loi_chung": "", "loi_he_thong": False,
           "next": request.GET.get("next") or request.POST.get("next") or ""}
    if request.method == "POST":
        ten = request.POST.get("username", "").strip()
        mk = request.POST.get("password", "")
        ctx["ten"] = ten
        if not ten:
            ctx["loi_ten"] = "Vui lòng nhập tên đăng nhập"
        if not mk:
            ctx["loi_mk"] = "Vui lòng nhập mật khẩu"
        if ten and mk:
            try:
                tk = authenticate(request, username=ten, password=mk)
            except DatabaseError:
                ctx["loi_he_thong"] = True
            else:
                if tk is None:
                    ctx["loi_chung"] = "Tên đăng nhập hoặc mật khẩu không đúng. Vui lòng thử lại."
                else:
                    login(request, tk)
                    nxt = ctx["next"]
                    if nxt and url_has_allowed_host_and_scheme(nxt, {request.get_host()}):
                        return redirect(nxt)
                    return redirect("hoi_vien_list")
    return render(request, "taikhoan/dang_nhap.html", ctx)


def _gui_ma(tk, kenh):
    """Tạo mã xác minh và gửi về email của tài khoản quản lý.
    Nếu chưa cấu hình Gmail (config/bi_mat.py) thì chỉ in mã ra terminal như bản demo."""
    ma = f"{secrets.randbelow(1_000_000):06d}"
    tk.maXacMinh = ma
    tk.hanMaXacMinh = timezone.now() + HIEU_LUC
    tk.save(update_fields=["maXacMinh", "hanMaXacMinh"])
    print(f"\n===== [MÃ XÁC MINH] gửi tới {tk.email}: {ma} (hiệu lực 5 phút) =====\n", flush=True)
    if settings.EMAIL_HOST_USER and tk.email:
        try:
            send_mail(
                "Mã xác minh đặt lại mật khẩu - Phòng Gym NT",
                f"Mã xác minh của bạn là: {ma}\n\nMã có hiệu lực trong 5 phút. "
                "Nếu bạn không yêu cầu đặt lại mật khẩu, hãy bỏ qua email này.",
                settings.DEFAULT_FROM_EMAIL, [tk.email],
            )
        except Exception:
            log.exception("Gửi email mã xác minh tới %s thất bại", tk.email)
            return
    log.info("Đã gửi mã xác minh tới %s (yêu cầu nhập: %s)", tk.email, kenh)


def quen_mat_khau(request):
    ctx = {"gia_tri": "", "loi": ""}
    if request.method == "POST":
        gt = request.POST.get("lien_he", "").strip()
        ctx["gia_tri"] = gt
        tk = TaiKhoan.objects.filter(Q(email__iexact=gt) | Q(soDienThoai=gt)).first() if gt else None
        if tk is None:
            ctx["loi"] = "Số điện thoại hoặc email này chưa được đăng ký"
        else:
            _gui_ma(tk, gt)
            request.session[KEY] = {"ten": tk.pk, "kenh": gt, "gui_luc": timezone.now().timestamp(), "ok": False}
            return redirect("xac_minh")
    return render(request, "taikhoan/quen_mat_khau.html", ctx)


def xac_minh(request):
    s = request.session.get(KEY)
    if not s:
        return redirect("quen_mat_khau")
    tk = TaiKhoan.objects.filter(pk=s["ten"]).first()
    con_cho = max(0, int(GUI_LAI_SAU - (timezone.now().timestamp() - s["gui_luc"])))
    ctx = {"kenh": s["kenh"], "loi": "", "con_cho": con_cho}
    if request.method == "POST":
        if request.POST.get("gui_lai") == "1":
            if con_cho == 0 and tk:
                _gui_ma(tk, s["kenh"])
                s["gui_luc"] = timezone.now().timestamp()
                request.session[KEY] = s
            return redirect("xac_minh")
        ma = "".join(request.POST.getlist("so")).strip()
        if tk and tk.maXacMinh and ma == tk.maXacMinh and tk.hanMaXacMinh and tk.hanMaXacMinh >= timezone.now():
            s["ok"] = True
            request.session[KEY] = s
            return redirect("dat_mat_khau")
        ctx["loi"] = "Mã xác minh không đúng hoặc đã hết hạn"
    return render(request, "taikhoan/xac_minh.html", ctx)


def dat_mat_khau(request):
    s = request.session.get(KEY)
    if not s or not s.get("ok"):
        return redirect("quen_mat_khau")
    ctx = {"loi_mk": "", "loi_xn": "", "loi_he_thong": False}
    if request.method == "POST":
        mk, xn = request.POST.get("mk", ""), request.POST.get("xn", "")
        if not mk:
            ctx["loi_mk"] = "Vui lòng nhập mật khẩu mới"
        if not xn:
            ctx["loi_xn"] = "Vui lòng nhập lại mật khẩu mới"
        elif mk and mk != xn:
            ctx["loi_xn"] = "Mật khẩu xác nhận không khớp"
        if not ctx["loi_mk"] and not ctx["loi_xn"]:
            try:
                tk = TaiKhoan.objects.get(pk=s["ten"])
                tk.set_password(mk)
                tk.maXacMinh = None
                tk.hanMaXacMinh = None
                tk.save()
            except (DatabaseError, TaiKhoan.DoesNotExist):
                ctx["loi_he_thong"] = True
            else:
                del request.session[KEY]
                return render(request, "taikhoan/thanh_cong.html")
    return render(request, "taikhoan/dat_mat_khau.html", ctx)
