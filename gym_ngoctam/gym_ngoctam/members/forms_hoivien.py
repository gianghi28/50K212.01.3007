"""Form UC02.1 Thêm hội viên và UC02.2 Chỉnh sửa – thông báo lỗi đúng theo đặc tả."""
import os
import re
import uuid

from django import forms
from django.core.files.storage import default_storage

from .models import GoiTap, HoiVien

SDT_RE = re.compile(r"^0\d{9}$")
ANH_TOI_DA = 5 * 1024 * 1024


def luu_anh_tam(file):
    """Lưu ảnh vừa chọn vào media/tam/ để không bị mất khi form báo lỗi. Trả về tên file tạm."""
    ext = os.path.splitext(file.name)[1].lower() or ".jpg"
    ten = default_storage.save(f"tam/{uuid.uuid4().hex}{ext}", file)
    return os.path.basename(ten)


class _ThongTinHoiVien(forms.Form):
    hoTen = forms.CharField(required=False, max_length=100)
    soDienThoai = forms.CharField(required=False, max_length=20)
    maGoi = forms.CharField(required=False)

    def __init__(self, *args, hoi_vien=None, **kwargs):
        self.hoi_vien = hoi_vien
        super().__init__(*args, **kwargs)

    def clean_hoTen(self):
        ten = " ".join(self.cleaned_data["hoTen"].split())
        if not ten:
            raise forms.ValidationError("Vui lòng nhập họ tên")
        return ten

    def clean_soDienThoai(self):
        sdt = self.cleaned_data["soDienThoai"].strip().replace(" ", "")
        if not sdt:
            raise forms.ValidationError("Vui lòng nhập số điện thoại")
        if not SDT_RE.match(sdt):
            raise forms.ValidationError("Số điện thoại không hợp lệ")
        qs = HoiVien.objects.filter(soDienThoai=sdt)
        if self.hoi_vien:
            qs = qs.exclude(pk=self.hoi_vien.pk)
        if qs.exists():
            raise forms.ValidationError("Số điện thoại đã tồn tại trong hệ thống")
        return sdt

    def _goi(self, bat_buoc):
        ma = (self.cleaned_data.get("maGoi") or "").strip()
        if not ma:
            if bat_buoc:
                raise forms.ValidationError("Vui lòng chọn gói tập")
            return None
        goi = GoiTap.objects.filter(pk=ma, trangThaiBan=GoiTap.TrangThaiBan.DANG_BAN).first()
        if goi is None:
            raise forms.ValidationError("Vui lòng chọn gói tập")
        return goi


class HoiVienThemForm(_ThongTinHoiVien):
    anh_tam = forms.CharField(required=False)

    def __init__(self, *args, files=None, **kwargs):
        self._file = (files or {}).get("anh")
        super().__init__(*args, **kwargs)

    def clean_maGoi(self):
        return self._goi(bat_buoc=True)

    def clean_anh_tam(self):
        if self._file:
            ext = os.path.splitext(self._file.name)[1].lower()
            if ext not in (".jpg", ".jpeg", ".png") or self._file.size > ANH_TOI_DA:
                raise forms.ValidationError("Ảnh phải là JPG hoặc PNG, tối đa 5 MB")
            return luu_anh_tam(self._file)
        token = os.path.basename(self.cleaned_data.get("anh_tam") or "")
        if token and default_storage.exists(f"tam/{token}"):
            return token
        raise forms.ValidationError("Vui lòng chọn ảnh hội viên")


class HoiVienSuaForm(_ThongTinHoiVien):
    baoLuu = forms.BooleanField(required=False)

    def clean_maGoi(self):
        return self._goi(bat_buoc=False)
