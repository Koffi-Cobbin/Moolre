"""
Base settings shared by dev/prod. See plan Section 10 (Configuration & Secrets).
"""
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="unsafe-dev-key-change-me")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "drf_spectacular",
    # Moolre domain apps (plan Section 3)
    "apps.wallets",
    "apps.payments",
    "apps.transfers",
    "apps.messaging",
    "apps.ledger",
    "apps.api",
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
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL", default="sqlite:///" + str(BASE_DIR / "db.sqlite3")),
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Accra"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Moolre Internal Platform API",
    "DESCRIPTION": "Internal wrapper around Moolre wallets, collections, "
                    "disbursements, SMS and WhatsApp (plan Section 8).",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ---------------------------------------------------------------------------
# Moolre configuration (plan Section 10)
# ---------------------------------------------------------------------------
MOOLRE = {
    "ENVIRONMENT": env("MOOLRE_ENV", default="sandbox"),  # sandbox | live
    "BASE_URL": {
        "sandbox": "https://sandbox.moolre.com",
        "live": "https://api.moolre.com",
    },
    "API_USER": env("MOOLRE_API_USER", default=None),
    "API_KEY": env("MOOLRE_API_KEY", default=None),        # not required in sandbox
    "API_PUBKEY": env("MOOLRE_API_PUBKEY", default=None),
    "API_VASKEY": env("MOOLRE_API_VASKEY", default=None),
    "DEFAULT_CURRENCY": "GHS",
    "TIMEOUT": env.int("MOOLRE_TIMEOUT", default=15),
    "MAX_RETRIES": env.int("MOOLRE_MAX_RETRIES", default=3),
}

# django-cryptography key for encrypting wallet secrets at rest (plan Section 4/10)
FIELD_ENCRYPTION_KEY = env("FIELD_ENCRYPTION_KEY", default=None)
