from django.urls import path

from . import webhooks

urlpatterns = [
    path("payments/", webhooks.payment_webhook, name="moolre-payment-webhook"),
]
