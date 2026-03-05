"""
Email integration for the personal assistant.
Provides functionality to read and process emails.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from email import message_from_bytes
from email.header import decode_header
import imaplib
import email


class EmailIntegration:
    """Integration with email via IMAP"""

    def __init__(self, imap_server: str, email_address: str, password: str):
        """
        Initialize Email integration.

        Args:
            imap_server: IMAP server address (e.g., imap.gmail.com)
            email_address: Email address
            password: Email password or app-specific password
        """
        self.imap_server = imap_server
        self.email_address = email_address
        self.password = password
        self.mail = None

    def connect(self) -> bool:
        """
        Connect to the IMAP server.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.mail = imaplib.IMAP4_SSL(self.imap_server)
            self.mail.login(self.email_address, self.password)
            return True
        except Exception as e:
            print(f"Error connecting to email server: {e}")
            return False

    def disconnect(self):
        """Disconnect from the IMAP server"""
        if self.mail:
            try:
                self.mail.logout()
            except:
                pass

    def get_recent_emails(
        self,
        mailbox: str = "INBOX",
        days: int = 7,
        limit: int = 50,
        unread_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get recent emails from a mailbox.

        Args:
            mailbox: Mailbox name (default: INBOX)
            days: Number of days to look back
            limit: Maximum number of emails to fetch
            unread_only: Only fetch unread emails

        Returns:
            List of email dictionaries
        """
        if not self.mail:
            if not self.connect():
                return []

        try:
            self.mail.select(mailbox)

            # Calculate date threshold
            threshold = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")

            # Build search criteria
            search_criteria = f'(SINCE {threshold})'
            if unread_only:
                search_criteria = f'(UNSEEN SINCE {threshold})'

            # Search for emails
            status, messages = self.mail.search(None, search_criteria)
            if status != "OK":
                return []

            email_ids = messages[0].split()
            email_ids = email_ids[-limit:]  # Get the most recent ones

            emails = []
            for email_id in reversed(email_ids):  # Most recent first
                email_data = self._fetch_email(email_id)
                if email_data:
                    emails.append(email_data)

            return emails

        except Exception as e:
            print(f"Error fetching emails: {e}")
            return []

    def get_unread_emails(
        self,
        mailbox: str = "INBOX",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get unread emails from a mailbox.

        Args:
            mailbox: Mailbox name (default: INBOX)
            limit: Maximum number of emails to fetch

        Returns:
            List of unread email dictionaries
        """
        if not self.mail:
            if not self.connect():
                return []

        try:
            self.mail.select(mailbox)

            # Search for unread emails
            status, messages = self.mail.search(None, 'UNSEEN')
            if status != "OK":
                return []

            email_ids = messages[0].split()
            email_ids = email_ids[-limit:]  # Get the most recent ones

            emails = []
            for email_id in reversed(email_ids):  # Most recent first
                email_data = self._fetch_email(email_id)
                if email_data:
                    emails.append(email_data)

            return emails

        except Exception as e:
            print(f"Error fetching unread emails: {e}")
            return []

    def search_emails(
        self,
        query: str,
        mailbox: str = "INBOX",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search for emails by subject or sender.

        Args:
            query: Search query
            mailbox: Mailbox name (default: INBOX)
            limit: Maximum number of emails to fetch

        Returns:
            List of matching email dictionaries
        """
        if not self.mail:
            if not self.connect():
                return []

        try:
            self.mail.select(mailbox)

            # Search in subject and from fields
            status, messages = self.mail.search(None, f'(OR SUBJECT "{query}" FROM "{query}")')
            if status != "OK":
                return []

            email_ids = messages[0].split()
            email_ids = email_ids[-limit:]  # Get the most recent ones

            emails = []
            for email_id in reversed(email_ids):  # Most recent first
                email_data = self._fetch_email(email_id)
                if email_data:
                    emails.append(email_data)

            return emails

        except Exception as e:
            print(f"Error searching emails: {e}")
            return []

    def mark_as_read(self, email_id: str, mailbox: str = "INBOX") -> bool:
        """
        Mark an email as read.

        Args:
            email_id: Email ID
            mailbox: Mailbox name

        Returns:
            True if successful, False otherwise
        """
        if not self.mail:
            if not self.connect():
                return False

        try:
            self.mail.select(mailbox)
            self.mail.store(email_id, '+FLAGS', '\\Seen')
            return True
        except Exception as e:
            print(f"Error marking email as read: {e}")
            return False

    def _fetch_email(self, email_id: bytes) -> Optional[Dict[str, Any]]:
        """
        Fetch and parse a single email.

        Args:
            email_id: Email ID

        Returns:
            Email dictionary or None if failed
        """
        try:
            status, msg_data = self.mail.fetch(email_id, '(RFC822)')
            if status != "OK":
                return None

            # Parse email
            email_body = msg_data[0][1]
            email_message = message_from_bytes(email_body)

            # Extract headers
            subject = self._decode_header(email_message.get("Subject", ""))
            from_ = self._decode_header(email_message.get("From", ""))
            to = self._decode_header(email_message.get("To", ""))
            date = email_message.get("Date", "")
            message_id = email_message.get("Message-ID", "")

            # Extract body
            body = self._extract_body(email_message)

            return {
                "id": email_id.decode(),
                "message_id": message_id,
                "subject": subject,
                "from": from_,
                "to": to,
                "date": date,
                "body": body,
            }

        except Exception as e:
            print(f"Error parsing email: {e}")
            return None

    def _decode_header(self, header: str) -> str:
        """Decode email header"""
        if not header:
            return ""

        decoded_parts = decode_header(header)
        decoded_header = ""

        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                decoded_header += part.decode(encoding or "utf-8", errors="ignore")
            else:
                decoded_header += part

        return decoded_header

    def _extract_body(self, email_message) -> str:
        """Extract email body text"""
        body = ""

        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                # Skip attachments
                if "attachment" in content_disposition:
                    continue

                # Extract text content
                if content_type == "text/plain":
                    try:
                        body += part.get_payload(decode=True).decode(errors="ignore")
                    except:
                        pass
                elif content_type == "text/html" and not body:
                    # Use HTML only if no plain text is available
                    try:
                        html_body = part.get_payload(decode=True).decode(errors="ignore")
                        # Simple HTML to text conversion (strip tags)
                        import re
                        body = re.sub('<[^<]+?>', '', html_body)
                    except:
                        pass
        else:
            try:
                body = email_message.get_payload(decode=True).decode(errors="ignore")
            except:
                body = str(email_message.get_payload())

        return body.strip()
