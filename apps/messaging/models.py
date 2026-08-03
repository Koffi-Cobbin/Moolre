"""
Messaging (SMS + WhatsApp) domain — models PLACEHOLDER.

Build order (plan Section 13): Milestone 6 ("Messaging": SMS send/status,
sender ID management, WhatsApp templates/send/status).

Planned models (plan Section 4, "messaging"):

    SenderId(name, approval_status, whitelisted)
    SmsMessage(senderid FK, recipient, message, ref UNIQUE, status, sent_at)
    WhatsAppTemplate(template_id, name, language, status, body,
                     placeholders JSON)
    WhatsAppMessage(template FK, recipient, ref UNIQUE, placeholders JSON,
                    status)

Not implemented yet — this file exists (with no models) so `apps.messaging`
is a valid, migratable Django app from the start of scaffolding.
"""
