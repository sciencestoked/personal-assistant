"""
Integration modules for the personal assistant.
Provides connectivity to Google Calendar, Notion, and Email.
"""

from .google_calendar import GoogleCalendarIntegration
from .notion import NotionIntegration
from .email import EmailIntegration

__all__ = [
    "GoogleCalendarIntegration",
    "NotionIntegration",
    "EmailIntegration",
]
