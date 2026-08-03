from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Plan Section 10: "dev.py forces sandbox"
MOOLRE["ENVIRONMENT"] = "sandbox"  # noqa: F405
