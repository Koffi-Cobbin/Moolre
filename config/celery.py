"""
Celery app definition — PLACEHOLDER.

Per the plan (Section 7), background polling/reconciliation jobs are
deferred to v2. v1 relies on synchronous calls + webhooks + on-demand
"check status" endpoints (Section 8), so nothing here is wired into
INSTALLED_APPS or settings yet.

When v2 starts, this becomes the standard:

    import os
    from celery import Celery

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    app = Celery("moolre_project")
    app.config_from_object("django.conf:settings", namespace="CELERY")
    app.autodiscover_tasks()
"""
