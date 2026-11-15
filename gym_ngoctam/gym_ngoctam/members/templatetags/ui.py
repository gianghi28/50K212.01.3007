from django import template

register = template.Library()


@register.filter
def vnd(value):
    """300000 -> 300.000"""
    try:
        return f"{int(value):,}".replace(",", ".")
    except (TypeError, ValueError):
        return value


@register.filter
def ten_goi(goi):
    """Hiển thị 'Gói [tên gói]' (không lặp chữ Gói nếu tên đã có sẵn)."""
    ten = str(goi.tenGoi if hasattr(goi, "tenGoi") else goi).strip()
    return ten if ten.lower().startswith("gói") else f"Gói {ten}"


@register.simple_tag
def static_v(path):
    """Đường dẫn file tĩnh kèm ?v=<thời điểm sửa file>: sửa CSS/JS xong chỉ cần F5, trình duyệt tự tải bản mới."""
    import os

    from django.contrib.staticfiles import finders
    from django.templatetags.static import static

    file = finders.find(path)
    ver = int(os.path.getmtime(file)) if file else 0
    return f"{static(path)}?v={ver}"
