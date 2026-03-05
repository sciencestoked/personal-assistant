"""
Google Calendar integration for the personal assistant.
Provides functionality to read and write calendar events.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import os.path
import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleCalendarIntegration:
    """Integration with Google Calendar API"""

    # If modifying these scopes, delete the token file.
    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly',
              'https://www.googleapis.com/auth/calendar.events']

    def __init__(self, credentials_path: str, token_path: str):
        """
        Initialize Google Calendar integration.

        Args:
            credentials_path: Path to Google credentials JSON file
            token_path: Path to store/load OAuth token
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.creds = None
        self.service = None

    def authenticate(self) -> bool:
        """
        Authenticate with Google Calendar API.

        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Load existing token if available
            if os.path.exists(self.token_path):
                self.creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)

            # Refresh or obtain new credentials if needed
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_path):
                        raise FileNotFoundError(
                            f"Credentials file not found: {self.credentials_path}\n"
                            "Please download credentials from Google Cloud Console."
                        )
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, self.SCOPES)
                    self.creds = flow.run_local_server(port=0)

                # Save credentials for next run
                os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
                with open(self.token_path, 'w') as token:
                    token.write(self.creds.to_json())

            # Build service
            self.service = build('calendar', 'v3', credentials=self.creds)
            return True

        except Exception as e:
            print(f"Authentication error: {e}")
            return False

    def get_upcoming_events(
        self,
        max_results: int = 10,
        days_ahead: int = 7,
        calendar_id: str = 'primary'
    ) -> List[Dict[str, Any]]:
        """
        Get upcoming calendar events.

        Args:
            max_results: Maximum number of events to return
            days_ahead: Number of days to look ahead
            calendar_id: Calendar ID (default is 'primary')

        Returns:
            List of event dictionaries
        """
        if not self.service:
            if not self.authenticate():
                return []

        try:
            now = datetime.utcnow().isoformat() + 'Z'
            end_time = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + 'Z'

            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=now,
                timeMax=end_time,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            return self._format_events(events)

        except HttpError as error:
            print(f"Error fetching events: {error}")
            return []

    def get_events_for_date(
        self,
        date: datetime,
        calendar_id: str = 'primary'
    ) -> List[Dict[str, Any]]:
        """
        Get events for a specific date.

        Args:
            date: Date to get events for
            calendar_id: Calendar ID (default is 'primary')

        Returns:
            List of event dictionaries
        """
        if not self.service:
            if not self.authenticate():
                return []

        try:
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)

            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=start_of_day.isoformat() + 'Z',
                timeMax=end_of_day.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            return self._format_events(events)

        except HttpError as error:
            print(f"Error fetching events: {error}")
            return []

    def create_event(
        self,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
        location: Optional[str] = None,
        calendar_id: str = 'primary'
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new calendar event.

        Args:
            summary: Event title
            start_time: Start time
            end_time: End time
            description: Event description
            location: Event location
            calendar_id: Calendar ID (default is 'primary')

        Returns:
            Created event dictionary or None if failed
        """
        if not self.service:
            if not self.authenticate():
                return None

        try:
            event = {
                'summary': summary,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'UTC',
                },
            }

            if description:
                event['description'] = description
            if location:
                event['location'] = location

            created_event = self.service.events().insert(
                calendarId=calendar_id,
                body=event
            ).execute()

            return self._format_event(created_event)

        except HttpError as error:
            print(f"Error creating event: {error}")
            return None

    def _format_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Format a single event for easier consumption"""
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))

        return {
            'id': event['id'],
            'summary': event.get('summary', 'No title'),
            'description': event.get('description', ''),
            'location': event.get('location', ''),
            'start': start,
            'end': end,
            'html_link': event.get('htmlLink', ''),
            'attendees': event.get('attendees', []),
        }

    def _format_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format multiple events"""
        return [self._format_event(event) for event in events]
