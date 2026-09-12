"""
backend/app/notifications/__init__.py
--------------------------------------
Notification subsystem for the Sentiment-Driven Stock Screener.

Public surface
--------------
    NotificationProvider   — abstract base for all providers
    ConsoleNotificationProvider — stdout/dev provider
    EmailNotificationProvider   — SMTP email provider
    NotificationService         — orchestrates delivery + idempotency
"""

from backend.app.notifications.base import NotificationProvider
from backend.app.notifications.console import ConsoleNotificationProvider
from backend.app.notifications.email import EmailNotificationProvider
from backend.app.notifications.service import NotificationService

__all__ = [
    "NotificationProvider",
    "ConsoleNotificationProvider",
    "EmailNotificationProvider",
    "NotificationService",
]
