from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import HoiVienForm
from .models import HoiVien


class HoiVienListView(LoginRequiredMixin, ListView):
    model = HoiVien
    template_name = "members/list.html"
    context_object_name = "hoi_viens"
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset().prefetch_related("cac_dang_ky__goiTap", "cac_dang_ky__cac_bao_luu")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(hoTen__icontains=q) | Q(soDienThoai__icontains=q) | Q(maHV__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["total"] = HoiVien.objects.count()
        return ctx


class HoiVienCreateView(LoginRequiredMixin, CreateView):
    model = HoiVien
    form_class = HoiVienForm
    template_name = "members/form.html"
    success_url = reverse_lazy("hoi_vien_list")
    extra_context = {"title": "Thêm hội viên"}

    def form_valid(self, form):
        messages.success(self.request, "Thêm hội viên thành công")
        return super().form_valid(form)


class HoiVienUpdateView(LoginRequiredMixin, UpdateView):
    model = HoiVien
    form_class = HoiVienForm
    template_name = "members/form.html"
    success_url = reverse_lazy("hoi_vien_list")
    extra_context = {"title": "Chỉnh sửa thông tin hội viên"}

    def form_valid(self, form):
        messages.success(self.request, "Cập nhật thành công")
        return super().form_valid(form)


class HoiVienDeleteView(LoginRequiredMixin, DeleteView):
    model = HoiVien
    template_name = "members/confirm_delete.html"
    success_url = reverse_lazy("hoi_vien_list")

    def form_valid(self, form):
        messages.success(self.request, "Xóa hội viên thành công")
        return super().form_valid(form)
