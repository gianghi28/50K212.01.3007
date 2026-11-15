import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("members", "0004_alter_hoivien_managers_alter_hoivien_sodienthoai_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="TepTin",
            fields=[
                ("ten", models.CharField(max_length=200, primary_key=True, serialize=False, verbose_name="Tên file")),
                ("noiDung", models.BinaryField(verbose_name="Nội dung")),
                ("ngayTao", models.DateTimeField(default=django.utils.timezone.now, verbose_name="Ngày tạo")),
            ],
            options={
                "verbose_name": "Tệp tin",
                "verbose_name_plural": "Tệp tin",
                "db_table": "TepTin",
            },
        ),
    ]
