"""
Notion integration for the personal assistant.
Provides functionality to read and search notes from Notion.
"""

from typing import List, Dict, Any, Optional
from notion_client import AsyncClient
from datetime import datetime


class NotionIntegration:
    """Integration with Notion API"""

    def __init__(self, api_key: str, database_id: Optional[str] = None):
        """
        Initialize Notion integration.

        Args:
            api_key: Notion API key
            database_id: Default database ID to query
        """
        self.client = AsyncClient(auth=api_key)
        self.database_id = database_id

    async def search_pages(
        self,
        query: str,
        page_size: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for pages in Notion.

        Args:
            query: Search query
            page_size: Maximum number of results

        Returns:
            List of page dictionaries
        """
        try:
            # The newer notion-client doesn't need filter for pages
            response = await self.client.search(
                query=query if query else "",
                page_size=page_size
            )
            return self._format_pages(response.get("results", []))
        except Exception as e:
            print(f"Error searching Notion: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def get_database_entries(
        self,
        database_id: Optional[str] = None,
        filter_dict: Optional[Dict[str, Any]] = None,
        page_size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get entries from a Notion database.

        Args:
            database_id: Database ID (uses default if not provided)
            filter_dict: Optional filter for database query
            page_size: Maximum number of results

        Returns:
            List of database entry dictionaries
        """
        db_id = database_id or self.database_id
        if not db_id:
            raise ValueError("No database ID provided")

        try:
            query_params = {"database_id": db_id, "page_size": page_size}
            if filter_dict:
                query_params["filter"] = filter_dict

            response = await self.client.databases.query(**query_params)
            return self._format_database_entries(response.get("results", []))
        except Exception as e:
            print(f"Error querying Notion database: {e}")
            return []

    async def get_page_content(self, page_id: str) -> Dict[str, Any]:
        """
        Get the content of a specific page.

        Args:
            page_id: Page ID

        Returns:
            Page content dictionary
        """
        try:
            # Get page metadata
            page = await self.client.pages.retrieve(page_id=page_id)

            # Get page blocks (content)
            blocks = await self.client.blocks.children.list(block_id=page_id, page_size=100)

            # Extract content recursively
            content = await self._extract_block_content_recursive(blocks.get("results", []))

            return {
                "metadata": self._format_page(page),
                "content": content
            }
        except Exception as e:
            print(f"Error getting page content: {e}")
            import traceback
            traceback.print_exc()
            return {"metadata": {}, "content": ""}

    async def get_recent_updates(
        self,
        days: int = 7,
        database_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recently updated pages (searches all accessible pages, not just databases).

        Args:
            days: Number of days to look back
            database_id: Not used anymore, kept for compatibility

        Returns:
            List of recently updated pages
        """
        try:
            # Use search with sort by last_edited_time instead of database query
            # This works for all pages, not just databases
            response = await self.client.search(
                query="",
                sort={
                    "direction": "descending",
                    "timestamp": "last_edited_time"
                },
                page_size=20
            )

            # Filter by date
            from datetime import timedelta, timezone
            threshold = datetime.now(timezone.utc) - timedelta(days=days)

            results = response.get("results", [])
            recent = []
            for page in results:
                last_edited = page.get("last_edited_time", "")
                if last_edited:
                    page_date = datetime.fromisoformat(last_edited.replace("Z", "+00:00"))
                    if page_date >= threshold:
                        recent.append(page)

            return self._format_pages(recent)
        except Exception as e:
            print(f"Error getting recent updates: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _format_page(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """Format a single page for easier consumption"""
        properties = page.get("properties", {})
        title = ""

        # Extract title from properties
        for key, value in properties.items():
            if value.get("type") == "title" and value.get("title"):
                title = "".join([t.get("plain_text", "") for t in value["title"]])
                break

        return {
            "id": page["id"],
            "title": title,
            "url": page.get("url", ""),
            "created_time": page.get("created_time", ""),
            "last_edited_time": page.get("last_edited_time", ""),
            "archived": page.get("archived", False),
        }

    def _format_pages(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format multiple pages"""
        return [self._format_page(page) for page in pages]

    def _format_database_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Format a database entry"""
        properties = entry.get("properties", {})
        formatted_props = {}

        for key, value in properties.items():
            prop_type = value.get("type")

            if prop_type == "title" and value.get("title"):
                formatted_props[key] = "".join([t.get("plain_text", "") for t in value["title"]])
            elif prop_type == "rich_text" and value.get("rich_text"):
                formatted_props[key] = "".join([t.get("plain_text", "") for t in value["rich_text"]])
            elif prop_type == "select" and value.get("select"):
                formatted_props[key] = value["select"].get("name", "")
            elif prop_type == "multi_select" and value.get("multi_select"):
                formatted_props[key] = [s.get("name", "") for s in value["multi_select"]]
            elif prop_type == "date" and value.get("date"):
                formatted_props[key] = value["date"].get("start", "")
            elif prop_type == "checkbox":
                formatted_props[key] = value.get("checkbox", False)
            elif prop_type == "number":
                formatted_props[key] = value.get("number")
            else:
                formatted_props[key] = str(value)

        return {
            "id": entry["id"],
            "url": entry.get("url", ""),
            "created_time": entry.get("created_time", ""),
            "last_edited_time": entry.get("last_edited_time", ""),
            "properties": formatted_props,
        }

    def _format_database_entries(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format multiple database entries"""
        return [self._format_database_entry(entry) for entry in entries]

    async def _extract_block_content_recursive(self, blocks: List[Dict[str, Any]], indent: int = 0) -> str:
        """Extract text content from blocks recursively"""
        content_parts = []
        prefix = "  " * indent

        for block in blocks:
            block_type = block.get("type")
            block_id = block.get("id")
            has_children = block.get("has_children", False)

            # Extract text based on block type
            if block_type in ["paragraph", "heading_1", "heading_2", "heading_3"]:
                rich_text = block.get(block_type, {}).get("rich_text", [])
                text = "".join([t.get("plain_text", "") for t in rich_text])
                if text:
                    if block_type.startswith("heading"):
                        content_parts.append(f"{prefix}## {text}")
                    else:
                        content_parts.append(f"{prefix}{text}")

            elif block_type in ["bulleted_list_item", "numbered_list_item"]:
                rich_text = block.get(block_type, {}).get("rich_text", [])
                text = "".join([t.get("plain_text", "") for t in rich_text])
                if text:
                    bullet = "•" if block_type == "bulleted_list_item" else "1."
                    content_parts.append(f"{prefix}{bullet} {text}")

            elif block_type == "to_do":
                rich_text = block.get("to_do", {}).get("rich_text", [])
                checked = block.get("to_do", {}).get("checked", False)
                text = "".join([t.get("plain_text", "") for t in rich_text])
                if text:
                    checkbox = "[x]" if checked else "[ ]"
                    content_parts.append(f"{prefix}{checkbox} {text}")

            elif block_type == "code":
                rich_text = block.get("code", {}).get("rich_text", [])
                text = "".join([t.get("plain_text", "") for t in rich_text])
                if text:
                    content_parts.append(f"{prefix}```\n{text}\n```")

            elif block_type == "quote":
                rich_text = block.get("quote", {}).get("rich_text", [])
                text = "".join([t.get("plain_text", "") for t in rich_text])
                if text:
                    content_parts.append(f"{prefix}> {text}")

            elif block_type == "divider":
                content_parts.append(f"{prefix}---")

            elif block_type == "table":
                content_parts.append(f"{prefix}[Table with {block.get('table', {}).get('table_width', 0)} columns]")

            # Recursively get children if they exist
            if has_children and block_id:
                try:
                    children = await self.client.blocks.children.list(block_id=block_id)
                    child_content = await self._extract_block_content_recursive(
                        children.get("results", []),
                        indent + 1
                    )
                    if child_content:
                        content_parts.append(child_content)
                except Exception as e:
                    print(f"Error getting children for block {block_id}: {e}")

        return "\n".join(content_parts)
