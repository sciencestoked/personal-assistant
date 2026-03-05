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
            response = await self.client.search(
                query=query,
                page_size=page_size,
                filter={"property": "object", "value": "page"}
            )
            return self._format_pages(response.get("results", []))
        except Exception as e:
            print(f"Error searching Notion: {e}")
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
            blocks = await self.client.blocks.children.list(block_id=page_id)

            return {
                "metadata": self._format_page(page),
                "content": self._extract_block_content(blocks.get("results", []))
            }
        except Exception as e:
            print(f"Error getting page content: {e}")
            return {"metadata": {}, "content": ""}

    async def get_recent_updates(
        self,
        days: int = 7,
        database_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recently updated pages from a database.

        Args:
            days: Number of days to look back
            database_id: Database ID (uses default if not provided)

        Returns:
            List of recently updated pages
        """
        db_id = database_id or self.database_id
        if not db_id:
            raise ValueError("No database ID provided")

        try:
            # Calculate date threshold
            from datetime import timedelta
            threshold = datetime.now() - timedelta(days=days)

            # Query with last_edited_time filter
            response = await self.client.databases.query(
                database_id=db_id,
                filter={
                    "timestamp": "last_edited_time",
                    "last_edited_time": {
                        "after": threshold.isoformat()
                    }
                },
                sorts=[
                    {
                        "timestamp": "last_edited_time",
                        "direction": "descending"
                    }
                ]
            )
            return self._format_database_entries(response.get("results", []))
        except Exception as e:
            # If Notion database is not configured, return empty list
            print(f"Error getting recent updates: {e}")
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

    def _extract_block_content(self, blocks: List[Dict[str, Any]]) -> str:
        """Extract text content from blocks"""
        content_parts = []

        for block in blocks:
            block_type = block.get("type")

            if block_type in ["paragraph", "heading_1", "heading_2", "heading_3", "bulleted_list_item", "numbered_list_item"]:
                rich_text = block.get(block_type, {}).get("rich_text", [])
                text = "".join([t.get("plain_text", "") for t in rich_text])
                if text:
                    content_parts.append(text)
            elif block_type == "code":
                rich_text = block.get("code", {}).get("rich_text", [])
                text = "".join([t.get("plain_text", "") for t in rich_text])
                if text:
                    content_parts.append(f"```\n{text}\n```")
            elif block_type == "quote":
                rich_text = block.get("quote", {}).get("rich_text", [])
                text = "".join([t.get("plain_text", "") for t in rich_text])
                if text:
                    content_parts.append(f"> {text}")

        return "\n\n".join(content_parts)
