import os
import urllib.parse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Trên Vercel có sẵn biến môi trường VERCEL=1
TREN_VERCEL = bool(os.environ.get("VERCEL"))

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "doi-khoa-nay-khi-dua-len-server")
DEBUG = os.environ.get("DJANGO_DEBUG", "0" if TREN_VERCEL else "1") == "1"
ALLOWED_HOSTS = ["*"]
# Vercel chạy HTTPS phía trước: báo cho Django biết để form (CSRF) không bị chặn
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = ["https://*.vercel.app"] + [
    o for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "members",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Ở máy: SQLite (db.sqlite3). Có biến DATABASE_URL (Vercel + Neon Postgres) thì dùng Postgres.
SQLITE = {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}
if os.environ.get("DATABASE_URL"):
    _u = urllib.parse.urlparse(os.environ["DATABASE_URL"])
    _q = dict(urllib.parse.parse_qsl(_u.query))
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": _u.path.lstrip("/"),
            "USER": urllib.parse.unquote(_u.username or ""),
            "PASSWORD": urllib.parse.unquote(_u.password or ""),
            "HOST": _u.hostname,
            "PORT": _u.port or 5432,
            "OPTIONS": {"sslmode": _q.get("sslmode", "require")},
            "CONN_MAX_AGE": 0,
        },
        # Dùng cho lệnh chuyen_len_postgres: đọc dữ liệu cũ từ db.sqlite3
        "cu": SQLITE,
    }
else:
    DATABASES = {"default": SQLITE}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "vi"
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
# Lưu giờ Việt Nam trực tiếp vào DB (mở DB Browser thấy đúng giờ, không bị lệch 7 tiếng)
USE_TZ = False

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
# Dùng Postgres (Vercel) thì ảnh hội viên lưu trong bảng TepTin; ở máy thì lưu thư mục media
STORAGES = {
    "default": {"BACKEND": "members.luu_tru.LuuTruCSDL" if os.environ.get("DATABASE_URL")
                else "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# Bảng TaiKhoan trong báo cáo dùng làm tài khoản đăng nhập
AUTH_USER_MODEL = "members.TaiKhoan"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "hoi_vien_list"
LOGOUT_REDIRECT_URL = "login"

# ---------------------------------------------------------------- Nhật ký hệ thống (logs/gym.log)
# Ghi lại: hội viên bị tự động xóa (UC02.3 – TH2), gửi mã xác minh (UC01)
# Trên Vercel không ghi được file nên nhật ký in ra mục Logs của Vercel.
if TREN_VERCEL:
    _handler = {"class": "logging.StreamHandler", "formatter": "don_gian"}
else:
    (BASE_DIR / "logs").mkdir(exist_ok=True)
    _handler = {"class": "logging.FileHandler", "filename": BASE_DIR / "logs" / "gym.log",
                "encoding": "utf-8", "formatter": "don_gian"}
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"don_gian": {"format": "{asctime}  {levelname}  {message}", "style": "{",
                                "datefmt": "%Y-%m-%d %H:%M:%S"}},
    "handlers": {"file_gym": _handler},
    "loggers": {"gym": {"handlers": ["file_gym"], "level": "INFO"}},
}

# ---------------------------------------------------------------- Gửi mã xác minh qua Gmail (UC01)
# Tạo file config/bi_mat.py (KHÔNG đưa lên GitHub) với 2 dòng:
#   EMAIL_HOST_USER = "tengmail@gmail.com"
#   EMAIL_HOST_PASSWORD = "mat khau ung dung 16 ky tu"
# Chưa có file này thì mã chỉ được in ra terminal như trước.
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_TIMEOUT = 15
# Trên Vercel: đặt 2 biến môi trường EMAIL_HOST_USER và EMAIL_HOST_PASSWORD
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
try:
    from .bi_mat import *  # noqa: F401,F403
except ImportError:
    pass
DEFAULT_FROM_EMAIL = f"Phòng Gym NT <{EMAIL_HOST_USER}>" if EMAIL_HOST_USER else "webmaster@localhost"
