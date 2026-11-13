"""Form cho UC03 – thông báo lỗi lấy đúng theo đặc tả UC03.1 / UC03.2."""
import re
from datetime import date

from django import forms

from .models import DangKyGoi, GoiTap


def _so_nguyen_duong(text):
    text = (text or "").strip()
    if not re.fullmatch(r"\d+", text):
        return None
    so = int(text)
    return so if so > 0 else None


def _gia(text):
    """Nhận '300000', '300.000', '300,000' → 300000. Sai hoặc ≤ 0 → None."""
    text = (text or "").strip().replace(".", "").replace(",", "").replace(" ", "")
    return _so_nguyen_duong(text)


class GoiTapThemForm(forms.Form):
    tenGoi = forms.CharField(required=False, max_length=50)
    thoiHan = forms.CharField(required=False)
    thoiHanBaoLuu = forms.CharField(required=False)
    gia = forms.CharField(required=False)

    def clean_tenGoi(self):
        ten = self.cleaned_data["tenGoi"].strip()
        if not ten:
            raise forms.ValidationError("Vui lòng nhập tên gói")
        # So sánh không phân biệt "Gói 1 tháng" và "1 tháng"
        chuan = re.sub(r"^gói\s+", "", ten, flags=re.I).lower()
        for goi in GoiTap.objects.all():
            if re.sub(r"^gói\s+", "", goi.tenGoi, flags=re.I).lower() == chuan:
                raise forms.ValidationError("Tên gói đã tồn tại")
        return ten

    def clean_thoiHan(self):
        raw = self.cleaned_data["thoiHan"].strip()
        if not raw:
            raise forms.ValidationError("Vui lòng nhập thời hạn")
        so = _so_nguyen_duong(raw)
        if so is None:
            raise forms.ValidationError("Thời hạn không hợp lệ")
        return so

    def clean_thoiHanBaoLuu(self):
        raw = self.cleaned_data["thoiHanBaoLuu"].strip()
        if not raw:
            raise forms.ValidationError("Vui lòng nhập thời hạn bảo lưu")
        so = _so_nguyen_duong(raw)
        if so is None:
            raise forms.ValidationError("Thời hạn bảo lưu không hợp lệ")
        return so

    def clean_gia(self):
        so = _gia(self.cleaned_data["gia"])
        if so is None:
            raise forms.ValidationError("Giá không hợp lệ")
        return so

    def clean(self):
        data = super().clean()
        han, bao_luu = data.get("thoiHan"), data.get("thoiHanBaoLuu")
        if han and bao_luu and bao_luu > han:
            self.add_error("thoiHanBaoLuu", "Thời hạn bảo lưu không được vượt quá thời hạn gói")
        return data


class GoiTapSuaForm(forms.Form):
    gia = forms.CharField(required=False)
    dangBan = forms.BooleanField(required=False)

    def clean_gia(self):
        so = _gia(self.cleaned_data["gia"])
        if so is None:
            raise forms.ValidationError("Giá không hợp lệ")
        return so


class LocLichSuForm(forms.Form):
    """Bộ lọc màn hình Lịch sử đăng ký gói (UC03.3)."""

    q = forms.CharField(required=False)
    tu_d = forms.CharField(required=False)
    tu_m = forms.CharField(required=False)
    tu_y = forms.CharField(required=False)
    den_d = forms.CharField(required=False)
    den_m = forms.CharField(required=False)
    den_y = forms.CharField(required=False)
    loai = forms.CharField(required=False)

    LOI_NGAY = "Khoảng thời gian không hợp lệ. Vui lòng chọn lại."

    def _ngay(self, prefix):
        d, m, y = (self.cleaned_data.get(f"{prefix}_{k}") or "" for k in ("d", "m", "y"))
        if not (d or m or y):
            return None  # không chọn → không lọc theo ngày này
        if not (d and m and y):
            raise forms.ValidationError(self.LOI_NGAY)
        try:
            return date(int(y), int(m), int(d))
        except ValueError:
            raise forms.ValidationError(self.LOI_NGAY)

    def clean(self):
        data = super().clean()
        tu = self._ngay("tu")
        den = self._ngay("den")
        hom_nay = date.today()
        if (tu and tu > hom_nay) or (den and den > hom_nay) or (tu and den and tu > den):
            raise forms.ValidationError(self.LOI_NGAY)
        data["tu_ngay"], data["den_ngay"] = tu, den
        if data.get("loai") not in dict(DangKyGoi.Loai.choices):
            data["loai"] = ""
        return data
