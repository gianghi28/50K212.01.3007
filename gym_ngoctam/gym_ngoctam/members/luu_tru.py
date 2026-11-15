"""Nơi lưu ảnh hội viên khi chạy trên Vercel: lưu thẳng vào bảng TepTin của Postgres
(Vercel không cho ghi file lên ổ đĩa). Ở máy cá nhân vẫn dùng thư mục media như bình thường."""
import mimetypes
import posixpath

from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.http import Http404, HttpResponse
from django.urls import reverse
from django.utils.deconstruct import deconstructible


@deconstructible
class LuuTruCSDL(Storage):
    def _model(self):
        from .models import TepTin
        return TepTin

    def _open(self, name, mode="rb"):
        tep = self._model().objects.filter(pk=name).first()
        if tep is None:
            raise FileNotFoundError(name)
        return ContentFile(bytes(tep.noiDung), name=name)

    def _save(self, name, content):
        if hasattr(content, "seek"):
            content.seek(0)
        du_lieu = content.read()
        self._model().objects.update_or_create(pk=name, defaults={"noiDung": du_lieu})
        return name

    def get_available_name(self, name, max_length=None):
        goc, duoi = posixpath.splitext(name)
        i = 1
        while self.exists(name):
            name = f"{goc}_{i}{duoi}"
            i += 1
        return name

    def exists(self, name):
        return self._model().objects.filter(pk=name).exists()

    def delete(self, name):
        self._model().objects.filter(pk=name).delete()

    def size(self, name):
        tep = self._model().objects.filter(pk=name).first()
        return len(tep.noiDung) if tep else 0

    def url(self, name):
        return reverse("tep_tin", args=[name])


def xem_tep(request, ten):
    """Trả ảnh lưu trong CSDL cho trình duyệt."""
    from .models import TepTin
    tep = TepTin.objects.filter(pk=ten).first()
    if tep is None:
        raise Http404
    loai = mimetypes.guess_type(ten)[0] or "application/octet-stream"
    res = HttpResponse(bytes(tep.noiDung), content_type=loai)
    res["Cache-Control"] = "public, max-age=86400"
    return res
