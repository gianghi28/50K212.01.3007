from django import forms

from .models import HoiVien


class HoiVienForm(forms.ModelForm):
    class Meta:
        model = HoiVien
        fields = ["hoTen", "soDienThoai", "anhDaiDien"]
        widgets = {
            "hoTen": forms.TextInput(attrs={"placeholder": "Nguyễn Văn A"}),
            "soDienThoai": forms.TextInput(attrs={"placeholder": "0901234567", "inputmode": "numeric"}),
        }
