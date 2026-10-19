
"""
Django settings for lifeline_backend project.
"""

from pathlib import Path
import os

from dotenv import load_dotenv
import dj_database_url


BASE_DIR = Path(__file__).resolve().parent.parent

# Local development: load .env from the repository root.
# Render environment variables remain available in production.
load_dotenv(BASE_DIR.parent / ".env")



SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-local-development-only-change-me",
)

DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        "ALLOWED_HOSTS",
        "lifeline-85fz.onrender.com,.onrender.com,127.0.0.1,localhost",
    ).split(",")
    if host.strip()
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CSRF_TRUSTED_ORIGINS",
        "https://lifeline-85fz.onrender.com",
    ).split(",")
    if origin.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
    "emergencies",
    "appointments",
    "screening",
    "inventory",
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

ROOT_URLCONF = "lifeline_backend.urls"

WSGI_APPLICATION = "lifeline_backend.wsgi.application"


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR.parent],
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


DATABASE_URL = os.getenv("DATABASE_URL", "")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is missing. Configure it in your local .env "
        "or your Render environment variables."
    )

DATABASES = {
    "default": dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=600,
        ssl_require=True,
    )
}



AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]



LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True



# STATIC FILES


STATIC_URL = "/static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

# Include only directories that actually exist.
# This prevents warnings for missing optional static folders.
STATIC_DIR_CANDIDATES = [
    ("css", BASE_DIR.parent / "css"),
    ("img", BASE_DIR.parent / "img"),
    ("donor/css", BASE_DIR.parent / "donor" / "css"),
    ("donor/image", BASE_DIR.parent / "donor" / "image"),
    ("organization/css", BASE_DIR.parent / "organization" / "css"),
    ("organization/img", BASE_DIR.parent / "organization" / "img"),
    (None, BASE_DIR.parent / "static"),
]

STATICFILES_DIRS = [
    (prefix, path) if prefix else path
    for prefix, path in STATIC_DIR_CANDIDATES
    if path.is_dir()
]



EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.smtp.EmailBackend",
)

EMAIL_HOST = os.getenv(
    "EMAIL_HOST",
    "smtp.gmail.com",
)

EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))

EMAIL_USE_TLS = (
    os.getenv("EMAIL_USE_TLS", "True").lower()
    in ("true", "1", "yes")
)

EMAIL_USE_SSL = False

EMAIL_HOST_USER = os.getenv(
    "EMAIL_HOST_USER",
    "",
)

EMAIL_HOST_PASSWORD = os.getenv(
    "EMAIL_HOST_PASSWORD",
    "",
)

DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL",
    EMAIL_HOST_USER,
)

# Email
# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'emergency.lifelineservices999@gmail.com'
EMAIL_HOST_PASSWORD = 'iwfsdstpueegnmni'  
DEFAULT_FROM_EMAIL = 'LifeLine Emergency Team <emergency.lifelineservices999@gmail.com>'
