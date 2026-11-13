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
