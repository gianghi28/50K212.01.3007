from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from members import views_taikhoan

urlpatterns = [
    path("admin/", admin.site.urls),
    path("dang-nhap/", views_taikhoan.dang_nhap, name="login"),
    path("quen-mat-khau/", views_taikhoan.quen_mat_khau, name="quen_mat_khau"),
    path("quen-mat-khau/xac-minh/", views_taikhoan.xac_minh, name="xac_minh"),
    path("quen-mat-khau/dat-mat-khau/", views_taikhoan.dat_mat_khau, name="dat_mat_khau"),
    path("dang-xuat/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("members.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
