from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("members", "0002_taikhoan_baoluu_dangkygoi_goitap_hoivien_luotcheckin_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="hoivien",
            options={
                "base_manager_name": "tat_ca",
                "ordering": ["-ngayTao"],
                "verbose_name": "Hội viên",
                "verbose_name_plural": "Hội viên",
            },
        ),
        migrations.AddField(
            model_name="hoivien",
            name="daXoa",
            field=models.BooleanField(default=False, verbose_name="Đã xóa"),
        ),
        migrations.AlterField(
            model_name="yeucaucheckin",
            name="trangThai",
            field=models.CharField(
                choices=[
                    ("Chờ xác nhận", "Chờ xác nhận"), ("Đã xác nhận", "Đã xác nhận"), ("Đã hủy", "Đã hủy"),
                    ("Hủy - hết hạn", "Hủy - hết hạn"), ("Khách hủy", "Khách hủy"), ("Lỗi hệ thống", "Lỗi hệ thống"),
                ],
                default="Chờ xác nhận", max_length=20, verbose_name="Trạng thái",
            ),
        ),
    ]
