"""
Signals fired when a PaymentRequest's status is resolved (plan Section 6,
step 4: "Fire a Django signal ... so other apps can react").
"""

import django.dispatch

payment_completed = django.dispatch.Signal()  # sender=PaymentRequest instance
payment_failed = django.dispatch.Signal()  # sender=PaymentRequest instance
