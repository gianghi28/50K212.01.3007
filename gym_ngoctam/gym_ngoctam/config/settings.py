from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "doi-khoa-nay-khi-dua-len-server"
DEBUG = True
ALLOWED_HOSTS = ["*"]

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

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "vi"
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
# Lưu giờ Việt Nam trực tiếp vào DB (mở DB Browser thấy đúng giờ, không bị lệch 7 tiếng)
USE_TZ = False

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Bảng TaiKhoan trong báo cáo dùng làm tài khoản đăng nhập
AUTH_USER_MODEL = "members.TaiKhoan"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "hoi_vien_list"
LOGOUT_REDIRECT_URL = "login"

# ---------------------------------------------------------------- Nhật ký hệ thống (logs/gym.log)
# Ghi lại: hội viên bị tự động xóa (UC02.3 – TH2), gửi mã xác minh (UC01)
(BASE_DIR / "logs").mkdir(exist_ok=True)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"don_gian": {"format": "{asctime}  {levelname}  {message}", "style": "{",
                                "datefmt": "%Y-%m-%d %H:%M:%S"}},
    "handlers": {"file_gym": {"class": "logging.FileHandler", "filename": BASE_DIR / "logs" / "gym.log",
                              "encoding": "utf-8", "formatter": "don_gian"}},
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
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
try:
    from .bi_mat import *  # noqa: F401,F403
except ImportError:
    pass
DEFAULT_FROM_EMAIL = f"Phòng Gym NT <{EMAIL_HOST_USER}>" if EMAIL_HOST_USER else "webmaster@localhost"
