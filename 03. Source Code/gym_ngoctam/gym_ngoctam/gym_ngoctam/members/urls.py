from django.urls import path

from . import views_baocao, views_checkin, views_goitap, views_hoivien

urlpatterns = [
    # UC02 – Quản lý hội viên
    path("", views_hoivien.hoi_vien_list, name="hoi_vien_list"),
    path("hoi-vien/them/", views_hoivien.hoi_vien_them, name="hoi_vien_them"),
    path("hoi-vien/thanh-toan/", views_hoivien.thanh_toan, name="thanh_toan"),
    path("hoi-vien/xoa/", views_hoivien.hoi_vien_xoa, name="hoi_vien_xoa"),
    path("hoi-vien/goi-y/", views_hoivien.goi_y_hoi_vien, name="goi_y_hoi_vien"),
    path("hoi-vien/<str:pk>/chuyen-nhuong/", views_hoivien.chuyen_nhuong, name="chuyen_nhuong"),
    path("hoi-vien/<str:pk>/", views_hoivien.hoi_vien_chi_tiet, name="hoi_vien_chi_tiet"),
    path("hoi-vien/<str:pk>/sua/", views_hoivien.hoi_vien_sua, name="hoi_vien_sua"),

    # UC03 – Quản lý gói tập
    path("goi-tap/", views_goitap.goi_tap_list, name="goi_tap_list"),
    path("goi-tap/them/", views_goitap.goi_tap_them, name="goi_tap_them"),
    path("goi-tap/lich-su-dang-ky/", views_goitap.lich_su_dang_ky, name="lich_su_dang_ky"),
    path("goi-tap/<str:pk>/", views_goitap.goi_tap_chi_tiet, name="goi_tap_chi_tiet"),
    path("goi-tap/<str:pk>/sua/", views_goitap.goi_tap_sua, name="goi_tap_sua"),

    # UC04 – Check-in
    path("check-in/", views_checkin.checkin_chinh, name="checkin_chinh"),
    path("check-in/so-cho/", views_checkin.checkin_so_cho, name="checkin_so_cho"),
    path("check-in/xac-nhan/<str:ma>/", views_checkin.checkin_xac_nhan, name="checkin_xac_nhan"),
    path("check-in/lich-su/", views_checkin.checkin_lich_su, name="checkin_lich_su"),
    path("check-in/lich-su/loc/", views_checkin.checkin_loc, name="checkin_loc"),
    path("check-in/lich-su/xuat-excel/", views_checkin.checkin_xuat_excel, name="checkin_xuat_excel"),
    path("check-in/ve-le/", views_checkin.ve_le, name="ve_le"),
    path("check-in/ve-le/thanh-toan/", views_checkin.ve_le_thanh_toan, name="ve_le_thanh_toan"),
    path("check-in/ve-le/<str:ma>/", views_checkin.ve_le_xong, name="ve_le_xong"),
    # UC05 – Báo cáo và thống kê
    path("bao-cao/", views_baocao.bao_cao_chinh, name="bao_cao"),
    path("bao-cao/doanh-thu/", views_baocao.doanh_thu, name="bc_doanh_thu"),
    path("bao-cao/hoi-vien-moi/", views_baocao.hoi_vien_moi, name="bc_hoi_vien_moi"),
    path("bao-cao/hoi-vien-dang-tap/", views_baocao.dang_tap, name="bc_dang_tap"),
    path("bao-cao/goi-tap-dang-ky/", views_baocao.goi_dang_ky, name="bc_goi_dang_ky"),
    # Màn hình hội viên quét QR (không cần đăng nhập)
    path("khach/check-in/", views_checkin.khach_checkin, name="khach_checkin"),
    path("khach/check-in/ket-qua/", views_checkin.khach_ket_qua, name="khach_ket_qua"),
    path("khach/check-in/trang-thai/", views_checkin.khach_trang_thai, name="khach_trang_thai"),
]
