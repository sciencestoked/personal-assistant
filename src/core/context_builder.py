"""
Context builder for the personal assistant.
Aggregates data from all sources (Calendar, Notion, Email) to build comprehensive context.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from ..integrations import GoogleCalendarIntegration, NotionIntegration, EmailIntegration
from .config import get_settings


class ContextBuilder:
    """Builds comprehensive context from all integrated sources"""

    def __init__(
        self,
        calendar: Optional[GoogleCalendarIntegration] = None,
        notion: Optional[NotionIntegration] = None,
        email: Optional[EmailIntegration] = None
    ):
        """
        Initialize context builder with integrations.

        Args:
            calendar: Google Calendar integration
            notion: Notion integration
            email: Email integration
        """
        self.calendar = calendar
        self.notion = notion
        self.email = email
        self.settings = get_settings()

    async def build_daily_context(self, target_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Build context for a specific day.

        Args:
            target_date: Date to build context for (defaults to today)

        Returns:
            Dictionary containing all relevant context for the day
        """
        if target_date is None:
            target_date = datetime.now()

        context = {
            "date": target_date.strftime("%Y-%m-%d"),
            "day_of_week": target_date.strftime("%A"),
            "calendar_events": [],
            "recent_notes": [],
            "unread_emails": [],
            "tasks": [],
            "summary": ""
        }

        # Gather calendar events
        if self.calendar:
            try:
                events = self.calendar.get_events_for_date(target_date)
                context["calendar_events"] = events
            except Exception as e:
                print(f"Error fetching calendar events: {e}")

        # Gather recent Notion updates
        if self.notion:
            try:
                recent_notes = await self.notion.get_recent_updates(days=1)
                context["recent_notes"] = recent_notes
            except Exception as e:
                print(f"Error fetching Notion updates: {e}")

        # Gather unread emails
        if self.email:
            try:
                unread = self.email.get_unread_emails(limit=20)
                context["unread_emails"] = unread
            except Exception as e:
                print(f"Error fetching emails: {e}")

        return context

    async def build_weekly_context(self) -> Dict[str, Any]:
        """
        Build context for the upcoming week.

        Returns:
            Dictionary containing weekly context
        """
        context = {
            "week_start": datetime.now().strftime("%Y-%m-%d"),
            "upcoming_events": [],
            "recent_notes": [],
            "important_emails": [],
            "summary": ""
        }

        # Gather upcoming calendar events
        if self.calendar:
            try:
                events = self.calendar.get_upcoming_events(max_results=50, days_ahead=7)
                context["upcoming_events"] = events
            except Exception as e:
                print(f"Error fetching calendar events: {e}")

        # Gather recent Notion updates
        if self.notion:
            try:
                recent_notes = await self.notion.get_recent_updates(days=7)
                context["recent_notes"] = recent_notes
            except Exception as e:
                print(f"Error fetching Notion updates: {e}")

        # Gather recent emails
        if self.email:
            try:
                recent_emails = self.email.get_recent_emails(days=7, limit=50)
                context["important_emails"] = recent_emails
            except Exception as e:
                print(f"Error fetching emails: {e}")

        return context

    async def search_context(self, query: str) -> Dict[str, Any]:
        """
        Search across all sources for a specific query.

        Args:
            query: Search query

        Returns:
            Dictionary containing search results from all sources
        """
        results = {
            "query": query,
            "notion_results": [],
            "email_results": [],
            "calendar_events": []
        }

        # Search Notion
        if self.notion:
            try:
                notion_results = await self.notion.search_pages(query)
                results["notion_results"] = notion_results
            except Exception as e:
                print(f"Error searching Notion: {e}")

        # Search Email
        if self.email:
            try:
                email_results = self.email.search_emails(query)
                results["email_results"] = email_results
            except Exception as e:
                print(f"Error searching emails: {e}")

        return results

    def build_context_summary(self, context: Dict[str, Any]) -> str:
        """
        Build a text summary of the context for LLM consumption.

        Args:
            context: Context dictionary

        Returns:
            Formatted text summary
        """
        summary_parts = []

        # Add date information
        if "date" in context:
            summary_parts.append(f"Date: {context['date']} ({context.get('day_of_week', '')})")

        # Add calendar events
        if context.get("calendar_events"):
            summary_parts.append("\n## Calendar Events:")
            for event in context["calendar_events"]:
                time = event.get("start", "No time")
                title = event.get("summary", "No title")
                summary_parts.append(f"- {time}: {title}")

        # Add upcoming events for weekly context
        if context.get("upcoming_events"):
            summary_parts.append("\n## Upcoming Events (Next 7 Days):")
            for event in context["upcoming_events"][:10]:  # Limit to 10
                time = event.get("start", "No time")
                title = event.get("summary", "No title")
                summary_parts.append(f"- {time}: {title}")

        # Add recent notes
        if context.get("recent_notes"):
            summary_parts.append("\n## Recent Notes:")
            for note in context["recent_notes"][:5]:  # Limit to 5
                title = note.get("title", "Untitled")
                updated = note.get("last_edited_time", "")
                summary_parts.append(f"- {title} (updated: {updated})")

        # Add unread emails
        if context.get("unread_emails"):
            summary_parts.append(f"\n## Unread Emails ({len(context['unread_emails'])}):")
            for email_msg in context["unread_emails"][:10]:  # Limit to 10
                subject = email_msg.get("subject", "No subject")
                from_ = email_msg.get("from", "Unknown sender")
                summary_parts.append(f"- From {from_}: {subject}")

        # Add tasks if present
        if context.get("tasks"):
            summary_parts.append("\n## Tasks:")
            for task in context["tasks"][:10]:  # Limit to 10
                summary_parts.append(f"- {task}")

        return "\n".join(summary_parts)

    async def extract_tasks_from_context(self, context: Dict[str, Any]) -> List[str]:
        """
        Extract actionable tasks from the context.

        Args:
            context: Context dictionary

        Returns:
            List of extracted tasks
        """
        tasks = []

        # Extract from calendar events
        for event in context.get("calendar_events", []):
            if event.get("description"):
                # Simple heuristic: look for action words
                desc = event["description"].lower()
                if any(word in desc for word in ["todo", "task", "action", "prepare", "complete"]):
                    tasks.append(f"Calendar: {event['summary']} - {event['description'][:100]}")

        # Extract from unread emails
        for email_msg in context.get("unread_emails", [])[:10]:
            subject = email_msg.get("subject", "")
            if any(word in subject.lower() for word in ["action required", "urgent", "deadline", "todo"]):
                tasks.append(f"Email: {subject}")

        return tasks
