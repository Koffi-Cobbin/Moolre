"""
Signals fired when a Transfer's status is resolved (mirrors
apps.payments.signals -- plan Section 6 pattern applied to disbursements).
"""

import django.dispatch

transfer_completed = django.dispatch.Signal()  # sender=Transfer instance
transfer_failed = django.dispatch.Signal()  # sender=Transfer instance
