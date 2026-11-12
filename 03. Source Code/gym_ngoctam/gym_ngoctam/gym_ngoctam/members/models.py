"""
Models theo đúng Chương 6 – Thiết kế cơ sở dữ liệu (báo cáo nhóm 50K212.01.3007).
Tên bảng (db_table) và tên cột (db_column) giữ y như báo cáo để mở bằng DB Browser thấy giống hệt.
"""
from datetime import timedelta

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

sdt_validator = RegexValidator(
    regex=r"^0\d{9}$",
    message="Số điện thoại phải gồm 10 chữ số và bắt đầu bằng 0.",
)


def ma_tiep_theo(model, prefix, do_dai=3):
    """Sinh mã kế tiếp dạng HV001, HV002... cho khóa chính kiểu VARCHAR."""
    lon_nhat = 0
    for ma in model._base_manager.filter(pk__startswith=prefix).values_list("pk", flat=True):
        so = ma[len(prefix):]
        if so.isdigit():
            lon_nhat = max(lon_nhat, int(so))
    return f"{prefix}{lon_nhat + 1:0{do_dai}d}"


class MaTuDongMixin(models.Model):
    """Tự gán mã (maHV, maGoi, ...) khi tạo mới nếu chưa có."""

    PREFIX = ""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.pk:
            self.pk = ma_tiep_theo(type(self), self.PREFIX)
        super().save(*args, **kwargs)


# ---------------------------------------------------------------- 6.2.9 TaiKhoan
class TaiKhoanManager(BaseUserManager):
    def create_user(self, tenDangNhap, email, password=None, **extra):
        tk = self.model(tenDangNhap=tenDangNhap, email=self.normalize_email(email), **extra)
        tk.set_password(password)
        tk.save(using=self._db)
        return tk

    def create_superuser(self, tenDangNhap, email, password=None, **extra):
        return self.create_user(tenDangNhap, email, password, **extra)


class TaiKhoan(AbstractBaseUser):
    tenDangNhap = models.CharField("Tên đăng nhập", max_length=100, primary_key=True)
    # Mật khẩu được lưu dạng mã hóa (hash) nên cần dài hơn 50 ký tự
    password = models.CharField("Mật khẩu", max_length=128, db_column="matKhau")
    email = models.CharField("Email", max_length=50, unique=True)
    soDienThoai = models.CharField("Số điện thoại", max_length=10, null=True, blank=True)
    maXacMinh = models.CharField("Mã xác minh", max_length=10, null=True, blank=True)
    hanMaXacMinh = models.DateTimeField("Hạn mã xác minh", null=True, blank=True)

    last_login = None  # bảng TaiKhoan trong báo cáo không có cột này

    objects = TaiKhoanManager()

    USERNAME_FIELD = "tenDangNhap"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["email"]

    class Meta:
        db_table = "TaiKhoan"
        verbose_name = verbose_name_plural = "Tài khoản"

    # Hệ thống chỉ có 1 người dùng là quản lý → có toàn quyền (dùng được trang /admin/)
    is_staff = True
    is_superuser = True

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

    def __str__(self):
        return self.tenDangNhap


# ---------------------------------------------------------------- 6.2.1 HoiVien
class HoiVienManager(models.Manager):
    """Mặc định chỉ lấy hội viên chưa bị xóa mềm (UC02.3)."""

    def get_queryset(self):
        return super().get_queryset().filter(daXoa=False)


class HoiVien(MaTuDongMixin):
    PREFIX = "HV"

    maHV = models.CharField("Mã hội viên", max_length=10, primary_key=True)
    hoTen = models.CharField("Họ tên", max_length=100)
    soDienThoai = models.CharField(
        "Số điện thoại", max_length=10, unique=True, validators=[sdt_validator],
        error_messages={"unique": "Số điện thoại đã tồn tại."},
    )
    anhDaiDien = models.ImageField("Ảnh đại diện", max_length=100, upload_to="anh_hoi_vien/", null=True, blank=True)
    ngayTao = models.DateTimeField("Ngày tạo", default=timezone.now)
    # Cột thêm để xóa mềm (UC02.3): không xóa hẳn để giữ lịch sử doanh thu, báo cáo
    daXoa = models.BooleanField("Đã xóa", default=False)

    objects = HoiVienManager()
    tat_ca = models.Manager()

    class Meta:
        db_table = "HoiVien"
        base_manager_name = "tat_ca"
        ordering = ["-ngayTao"]
        verbose_name = verbose_name_plural = "Hội viên"

    def __str__(self):
        return f"{self.maHV} - {self.hoTen}"

    # ---- các hàm tiện ích dùng cho giao diện / nghiệp vụ
    def dang_ky_hien_tai(self):
        """Lần đăng ký gói mới nhất (theo ngày kết thúc), bỏ qua dòng 'Chuyển nhượng đi'."""
        return (self.cac_dang_ky.exclude(loai=DangKyGoi.Loai.CHUYEN_DI)
                .order_by("-ngayKetThuc", "-ngayDangKy").first())

    def bao_luu_hien_tai(self):
        dk = self.dang_ky_hien_tai()
        if dk is None:
            return None
        return dk.cac_bao_luu.filter(trangThai=BaoLuu.TrangThai.DANG_BAO_LUU).first()

    @property
    def dang_bao_luu(self):
        return self.bao_luu_hien_tai() is not None

    @property
    def trang_thai(self):
        """Còn hạn / Hết hạn / Đang bảo lưu / Chưa có gói (tính từ gói tập, không lưu cứng)."""
        dk = self.dang_ky_hien_tai()
        if dk is None:
            return "Chưa có gói"
        if self.bao_luu_hien_tai():
            return "Đang bảo lưu"
        return "Còn hạn" if dk.ngayKetThuc.date() > timezone.now().date() else "Hết hạn"

    @property
    def so_ngay_con_lai(self):
        """Ngày kết thúc − hôm nay. Khi đang bảo lưu: giữ nguyên (đóng băng) số ngày lúc bắt đầu bảo lưu."""
        dk = self.dang_ky_hien_tai()
        if dk is None:
            return 0
        bl = self.bao_luu_hien_tai()
        if bl:
            return max((dk.ngayKetThuc.date() - bl.ngayKetThuc.date()).days, 0)
        return max((dk.ngayKetThuc.date() - timezone.now().date()).days, 0)

    @property
    def da_chuyen_nhuong_het(self):
        """Lần giao dịch gần nhất là 'Chuyển nhượng đi' → không còn gói tập."""
        moi_nhat = self.cac_dang_ky.order_by("-ngayDangKy").first()
        return bool(moi_nhat and moi_nhat.loai == DangKyGoi.Loai.CHUYEN_DI)

    @property
    def da_dung_quyen_bao_luu(self):
        dk = self.dang_ky_hien_tai()
        return bool(dk and dk.cac_bao_luu.exists())


def ket_thuc_bao_luu_het_han():
    """UC02.6 – TH2: tới 'Bảo lưu đến ngày' thì tự chuyển về Còn hạn."""
    now = timezone.now()
    for bl in BaoLuu.objects.filter(trangThai=BaoLuu.TrangThai.DANG_BAO_LUU, ngayKetThuc__lte=now):
        bl.trangThai = BaoLuu.TrangThai.DA_KET_THUC
        bl.soNgayDaDung = (bl.ngayKetThuc.date() - bl.ngayBatDau.date()).days
        bl.save(update_fields=["trangThai", "soNgayDaDung"])


# ---------------------------------------------------------------- 6.2.2 GoiTap
class GoiTap(MaTuDongMixin):
    PREFIX = "GT"

    class TrangThaiBan(models.TextChoices):
        DANG_BAN = "Đang bán", "Đang bán"
        NGUNG_BAN = "Ngừng bán", "Ngừng bán"

    maGoi = models.CharField("Mã gói tập", max_length=10, primary_key=True)
    tenGoi = models.CharField("Tên gói tập", max_length=50)
    thoiHan = models.IntegerField("Thời hạn (ngày)")
    gia = models.DecimalField("Giá", max_digits=18, decimal_places=2)
    thoiHanBaoLuu = models.IntegerField("Thời hạn bảo lưu (ngày)", null=True, blank=True, default=0)
    trangThaiBan = models.CharField("Trạng thái bán", max_length=20, choices=TrangThaiBan.choices,
                                    default=TrangThaiBan.DANG_BAN)

    class Meta:
        db_table = "GoiTap"
        ordering = ["thoiHan"]
        verbose_name = verbose_name_plural = "Gói tập"
        constraints = [
            models.CheckConstraint(condition=Q(thoiHan__gt=0), name="ck_goitap_thoihan"),
            models.CheckConstraint(condition=Q(gia__gte=0), name="ck_goitap_gia"),
            models.CheckConstraint(condition=Q(thoiHanBaoLuu__gte=0), name="ck_goitap_thoihanbaoluu"),
        ]

    def __str__(self):
        return self.tenGoi

    @property
    def dang_ban(self):
        return self.trangThaiBan == self.TrangThaiBan.DANG_BAN

    def hoi_vien_da_dang_ky(self):
        """Các hội viên từng đăng ký gói này (mỗi người 1 lần, mới nhất trước)."""
        da_co, ket_qua = set(), []
        for dk in self.cac_dang_ky.select_related("hoiVien").filter(hoiVien__daXoa=False).order_by("-ngayDangKy"):
            if dk.hoiVien_id not in da_co:
                da_co.add(dk.hoiVien_id)
                ket_qua.append(dk.hoiVien)
        return ket_qua

    def hoi_vien_dang_dung(self):
        """Các hội viên có gói hiện tại là gói này và chưa hết hạn."""
        ket_qua = []
        for hv in self.hoi_vien_da_dang_ky():
            dk = hv.dang_ky_hien_tai()
            if dk and dk.goiTap_id == self.pk and hv.trang_thai in ("Còn hạn", "Đang bảo lưu"):
                ket_qua.append(hv)
        return ket_qua


# ---------------------------------------------------------------- 6.2.3 DangKyGoi
class DangKyGoi(MaTuDongMixin):
    PREFIX = "DK"

    class Loai(models.TextChoices):
        DANG_KY_MOI = "Đăng ký mới", "Đăng ký mới"
        GIA_HAN = "Gia hạn", "Gia hạn"
        NANG_CAP = "Nâng cấp/Đổi gói", "Nâng cấp/Đổi gói"
        CHUYEN_DI = "Chuyển nhượng đi", "Chuyển nhượng đi"
        NHAN_CHUYEN = "Nhận chuyển nhượng", "Nhận chuyển nhượng"

    maDK = models.CharField("Mã đăng ký", max_length=10, primary_key=True)
    hoiVien = models.ForeignKey(HoiVien, on_delete=models.CASCADE, db_column="maHV",
                                related_name="cac_dang_ky", verbose_name="Hội viên")
    goiTap = models.ForeignKey(GoiTap, on_delete=models.PROTECT, db_column="maGoi",
                               related_name="cac_dang_ky", verbose_name="Gói tập")
    loai = models.CharField("Loại", max_length=20, choices=Loai.choices, default=Loai.DANG_KY_MOI)
    soTien = models.DecimalField("Số tiền", max_digits=18, decimal_places=2)
    ngayDangKy = models.DateTimeField("Ngày đăng ký", default=timezone.now)
    ngayBatDau = models.DateTimeField("Ngày bắt đầu")
    ngayKetThuc = models.DateTimeField("Ngày kết thúc")
    soNgayCongDon = models.IntegerField("Số ngày cộng dồn", null=True, blank=True, default=0)

    class Meta:
        db_table = "DangKyGoi"
        ordering = ["-ngayDangKy"]
        verbose_name = verbose_name_plural = "Đăng ký gói"
        constraints = [
            models.CheckConstraint(condition=Q(soTien__gte=0), name="ck_dangkygoi_sotien"),
            models.CheckConstraint(condition=Q(ngayKetThuc__gte=F("ngayBatDau")), name="ck_dangkygoi_ngay"),
            models.CheckConstraint(condition=Q(soNgayCongDon__gte=0), name="ck_dangkygoi_congdon"),
        ]

    def __str__(self):
        return f"{self.maDK} - {self.hoiVien.hoTen} - {self.goiTap.tenGoi}"

    @staticmethod
    def tinh_ngay_ket_thuc(ngay_bat_dau, thoi_han, so_ngay_cong_don=0):
        return ngay_bat_dau + timedelta(days=thoi_han + (so_ngay_cong_don or 0))


# ---------------------------------------------------------------- 6.2.4 ThanhToan
class ThanhToan(MaTuDongMixin):
    PREFIX = "GD"

    class HinhThuc(models.TextChoices):
        TIEN_MAT = "Tiền mặt", "Tiền mặt"
        CHUYEN_KHOAN = "Chuyển khoản", "Chuyển khoản"

    class TrangThai(models.TextChoices):
        CHO = "Chờ thanh toán", "Chờ thanh toán"
        THANH_CONG = "Thành công", "Thành công"
        DA_HUY = "Đã hủy", "Đã hủy"

    maGiaoDich = models.CharField("Mã giao dịch", max_length=10, primary_key=True)
    # Cho phép trống: giao dịch bán vé lẻ (UC04.4) không gắn với lần đăng ký gói nào
    dangKy = models.ForeignKey(DangKyGoi, on_delete=models.CASCADE, db_column="maDK", null=True, blank=True,
                               related_name="cac_thanh_toan", verbose_name="Đăng ký gói")
    soTien = models.DecimalField("Số tiền", max_digits=18, decimal_places=2)
    hinhThuc = models.CharField("Hình thức", max_length=20, choices=HinhThuc.choices)
    thoiGian = models.DateTimeField("Thời gian", default=timezone.now)
    nhanVienThu = models.CharField("Nhân viên thu", max_length=50)
    trangThai = models.CharField("Trạng thái", max_length=20, choices=TrangThai.choices,
                                 default=TrangThai.THANH_CONG)

    class Meta:
        db_table = "ThanhToan"
        ordering = ["-thoiGian"]
        verbose_name = verbose_name_plural = "Thanh toán"
        constraints = [
            models.CheckConstraint(condition=Q(soTien__gt=0), name="ck_thanhtoan_sotien"),
        ]

    def __str__(self):
        return f"{self.maGiaoDich} - {self.soTien:,.0f}đ"


# ---------------------------------------------------------------- 6.2.5 VeLe
class VeLe(MaTuDongMixin):
    PREFIX = "VL"
    GIA_MAC_DINH = 40000

    maVe = models.CharField("Mã vé", max_length=10, primary_key=True)
    giaoDich = models.OneToOneField(ThanhToan, on_delete=models.PROTECT, db_column="maGiaoDich",
                                    related_name="ve_le", verbose_name="Giao dịch")
    ngayMua = models.DateTimeField("Ngày mua", default=timezone.now)
    giaVe = models.DecimalField("Giá vé", max_digits=18, decimal_places=2, default=GIA_MAC_DINH)
    hoTen = models.CharField("Họ tên", max_length=100, null=True, blank=True)
    soDienThoai = models.CharField("Số điện thoại", max_length=10, null=True, blank=True)

    class Meta:
        db_table = "VeLe"
        ordering = ["-ngayMua"]
        verbose_name = verbose_name_plural = "Vé lẻ"
        constraints = [
            models.CheckConstraint(condition=Q(giaVe__gte=0), name="ck_vele_giave"),
        ]

    def __str__(self):
        return f"{self.maVe} - {self.hoTen or 'Khách vãng lai'}"


# ---------------------------------------------------------------- 6.2.6 BaoLuu
class BaoLuu(MaTuDongMixin):
    PREFIX = "BL"

    class TrangThai(models.TextChoices):
        DANG_BAO_LUU = "Đang bảo lưu", "Đang bảo lưu"
        DA_KET_THUC = "Đã kết thúc", "Đã kết thúc"

    maBL = models.CharField("Mã bảo lưu", max_length=10, primary_key=True)
    dangKy = models.ForeignKey(DangKyGoi, on_delete=models.CASCADE, db_column="maDK",
                               related_name="cac_bao_luu", verbose_name="Đăng ký gói")
    ngayBatDau = models.DateTimeField("Ngày bắt đầu")
    ngayKetThuc = models.DateTimeField("Ngày kết thúc")
    soNgayDaDung = models.IntegerField("Số ngày đã dùng", null=True, blank=True, default=0)
    trangThai = models.CharField("Trạng thái", max_length=20, choices=TrangThai.choices,
                                 default=TrangThai.DANG_BAO_LUU)

    class Meta:
        db_table = "BaoLuu"
        ordering = ["-ngayBatDau"]
        verbose_name = verbose_name_plural = "Bảo lưu"
        constraints = [
            models.CheckConstraint(condition=Q(ngayKetThuc__gte=F("ngayBatDau")), name="ck_baoluu_ngay"),
            models.CheckConstraint(condition=Q(soNgayDaDung__gte=0), name="ck_baoluu_songaydadung"),
        ]

    def __str__(self):
        return f"{self.maBL} - {self.dangKy.hoiVien.hoTen}"


# ---------------------------------------------------------------- 6.2.7 YeuCauCheckin
class YeuCauCheckin(MaTuDongMixin):
    PREFIX = "YC"

    class TrangThai(models.TextChoices):
        CHO_XAC_NHAN = "Chờ xác nhận", "Chờ xác nhận"
        DA_XAC_NHAN = "Đã xác nhận", "Đã xác nhận"
        DA_HUY = "Đã hủy", "Đã hủy"                  # quản lý hủy (không đúng người)
        HUY_HET_HAN = "Hủy - hết hạn", "Hủy - hết hạn"  # gói hết hạn, quản lý hủy
        KHACH_HUY = "Khách hủy", "Khách hủy"         # hội viên bấm "Nhập lại số điện thoại"
        LOI = "Lỗi hệ thống", "Lỗi hệ thống"

    maYC = models.CharField("Mã yêu cầu", max_length=10, primary_key=True)
    hoiVien = models.ForeignKey(HoiVien, on_delete=models.CASCADE, db_column="maHV",
                                related_name="cac_yeu_cau_checkin", verbose_name="Hội viên")
    thoiGianGui = models.DateTimeField("Thời gian gửi", default=timezone.now)
    trangThai = models.CharField("Trạng thái", max_length=20, choices=TrangThai.choices,
                                 default=TrangThai.CHO_XAC_NHAN)

    class Meta:
        db_table = "YeuCauCheckin"
        ordering = ["-thoiGianGui"]
        verbose_name = verbose_name_plural = "Yêu cầu check-in"

    def __str__(self):
        return f"{self.maYC} - {self.hoiVien.hoTen}"


# ---------------------------------------------------------------- 6.2.8 LuotCheckin
class LuotCheckin(MaTuDongMixin):
    PREFIX = "LC"

    class KetQua(models.TextChoices):
        THANH_CONG = "Thành công", "Thành công"
        BAO_LUU_KET_THUC = "Bảo lưu kết thúc", "Bảo lưu kết thúc"
        KHONG_THANH_CONG = "Không thành công", "Không thành công"

    maLuot = models.CharField("Mã lượt", max_length=10, primary_key=True)
    yeuCau = models.ForeignKey(YeuCauCheckin, on_delete=models.CASCADE, db_column="maYC",
                               related_name="cac_luot", verbose_name="Yêu cầu")
    hoiVien = models.ForeignKey(HoiVien, on_delete=models.CASCADE, db_column="maHV",
                                related_name="cac_luot_checkin", verbose_name="Hội viên")
    thoiGian = models.DateTimeField("Thời gian", default=timezone.now)
    ketQua = models.CharField("Kết quả", max_length=20, choices=KetQua.choices)

    class Meta:
        db_table = "LuotCheckin"
        ordering = ["-thoiGian"]
        verbose_name = verbose_name_plural = "Lượt check-in"

    def __str__(self):
        return f"{self.maLuot} - {self.hoiVien.hoTen} - {self.ketQua}"
