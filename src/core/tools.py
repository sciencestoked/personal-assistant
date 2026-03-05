"""
Tool/Function system for agentic behavior.
Allows the LLM to call functions and see results.
"""

from typing import Dict, Any, List, Callable, Optional
from datetime import datetime
import json
import inspect


class Tool:
    """Represents a callable tool/function"""

    def __init__(
        self,
        name: str,
        description: str,
        function: Callable,
        parameters: Dict[str, Any],
        requires_integration: Optional[str] = None
    ):
        self.name = name
        self.description = description
        self.function = function
        self.parameters = parameters
        self.requires_integration = requires_integration

    def to_dict(self) -> Dict[str, Any]:
        """Convert to LLM-friendly format"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "requires": self.requires_integration or "none"
        }

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool and return result"""
        try:
            # Call the function
            if inspect.iscoroutinefunction(self.function):
                result = await self.function(**kwargs)
            else:
                result = self.function(**kwargs)

            return {
                "success": True,
                "result": result,
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "result": None,
                "error": str(e)
            }


class ToolRegistry:
    """Registry of all available tools"""

    def __init__(self):
        self.tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        """Register a tool"""
        self.tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name"""
        return self.tools.get(name)

    def get_all_tools(self) -> List[Tool]:
        """Get all registered tools"""
        return list(self.tools.values())

    def get_available_tools(self, available_integrations: Dict[str, bool]) -> List[Tool]:
        """Get tools that can be used based on available integrations"""
        available = []
        for tool in self.tools.values():
            if tool.requires_integration:
                if available_integrations.get(tool.requires_integration):
                    available.append(tool)
            else:
                available.append(tool)
        return available

    def tools_to_prompt(self, available_integrations: Dict[str, bool]) -> str:
        """Generate prompt describing available tools"""
        tools = self.get_available_tools(available_integrations)

        if not tools:
            return "You have no tools available. All integrations are disabled."

        prompt = "## AVAILABLE TOOLS\n\nYou can call these functions to perform actions:\n\n"

        for tool in tools:
            prompt += f"### {tool.name}\n"
            prompt += f"**Description**: {tool.description}\n"
            prompt += f"**Parameters**: {json.dumps(tool.parameters, indent=2)}\n"
            if tool.requires_integration:
                prompt += f"**Requires**: {tool.requires_integration} integration\n"
            prompt += "\n"

        prompt += """
## HOW TO USE TOOLS

When you want to use a tool, respond with a JSON object in this EXACT format:

```json
{
  "thought": "Why I'm calling this function",
  "tool": "tool_name",
  "parameters": {
    "param1": "value1",
    "param2": "value2"
  }
}
```

**IMPORTANT RULES**:
1. Only call ONE tool at a time
2. Wait for the result before calling another tool
3. The result will be shown to you, then you can decide what to do next
4. If a tool fails, explain the error to the user
5. If you don't need to call a tool, just respond normally

**Example**:
User: "What's on my calendar today?"
You:
```json
{
  "thought": "User wants to see today's calendar events, I'll use get_calendar_events",
  "tool": "get_calendar_events",
  "parameters": {
    "date": "2026-03-05"
  }
}
```

Then you'll receive the result and can present it to the user.

**CRITICAL - NEVER HALLUCINATE**:
⚠️ When you receive tool results, you MUST show ONLY what was actually returned.
⚠️ DO NOT make up tasks, events, notes, or any data that wasn't in the result.
⚠️ If the result is empty or null, say so - don't invent content.
⚠️ ONLY show data that was explicitly in the tool result JSON.

Example - CORRECT ✅:
Tool result: [{"title": "Meeting", "time": "10am"}]
Your response: "You have 1 event: Meeting at 10am"

Example - WRONG ❌:
Tool result: [{"title": "Meeting"}]
Your response: "You have: 1. Meeting at 10am, 2. Lunch at noon, 3. Call John"
^^^ THIS IS HALLUCINATION - items 2 and 3 weren't in the result!

If you hallucinate data, you will lose the user's trust permanently.
"""

        return prompt


def create_tool_registry(context_builder) -> ToolRegistry:
    """Create and populate tool registry with all available tools"""
    registry = ToolRegistry()

    # Calendar tools
    if context_builder.calendar:
        async def get_calendar_events_wrapper(date):
            dt = datetime.fromisoformat(date) if isinstance(date, str) else date
            return context_builder.calendar.get_events_for_date(dt)

        registry.register(Tool(
            name="get_calendar_events",
            description="Get calendar events for a specific date",
            function=get_calendar_events_wrapper,
            parameters={
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format"
                    }
                },
                "required": ["date"]
            },
            requires_integration="calendar"
        ))

        registry.register(Tool(
            name="get_upcoming_events",
            description="Get upcoming calendar events for the next N days",
            function=lambda days=7: context_builder.calendar.get_upcoming_events(
                max_results=50, days_ahead=days
            ),
            parameters={
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Number of days to look ahead (default: 7)"
                    }
                },
                "required": []
            },
            requires_integration="calendar"
        ))

        registry.register(Tool(
            name="create_calendar_event",
            description="Create a new calendar event",
            function=lambda summary, start_time, end_time, description="", location="":
                context_builder.calendar.create_event(
                    summary=summary,
                    start_time=datetime.fromisoformat(start_time) if isinstance(start_time, str) else start_time,
                    end_time=datetime.fromisoformat(end_time) if isinstance(end_time, str) else end_time,
                    description=description,
                    location=location
                ),
            parameters={
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "Event title"},
                    "start_time": {"type": "string", "description": "Start time in ISO format"},
                    "end_time": {"type": "string", "description": "End time in ISO format"},
                    "description": {"type": "string", "description": "Event description (optional)"},
                    "location": {"type": "string", "description": "Event location (optional)"}
                },
                "required": ["summary", "start_time", "end_time"]
            },
            requires_integration="calendar"
        ))

    # Notion tools
    if context_builder.notion:
        async def search_notion_wrapper(query):
            return await context_builder.notion.search_pages(query)

        async def get_recent_notion_wrapper(days=7):
            return await context_builder.notion.get_recent_updates(days=days)

        async def get_notion_page_content_wrapper(page_id):
            return await context_builder.notion.get_page_content(page_id)

        registry.register(Tool(
            name="search_notion",
            description="Search for pages/notes in Notion",
            function=search_notion_wrapper,
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            },
            requires_integration="notion"
        ))

        registry.register(Tool(
            name="get_recent_notion_updates",
            description="Get recently updated Notion pages",
            function=get_recent_notion_wrapper,
            parameters={
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Number of days to look back (default: 7)"
                    }
                },
                "required": []
            },
            requires_integration="notion"
        ))

        registry.register(Tool(
            name="get_notion_page_content",
            description="Get the full content of a specific Notion page by its ID",
            function=get_notion_page_content_wrapper,
            parameters={
                "type": "object",
                "properties": {
                    "page_id": {
                        "type": "string",
                        "description": "The Notion page ID (without dashes, e.g., 2eea77fe03f78098a233c3c016f0d857)"
                    }
                },
                "required": ["page_id"]
            },
            requires_integration="notion"
        ))

    # Email tools
    if context_builder.email:
        registry.register(Tool(
            name="get_unread_emails",
            description="Get unread emails from inbox",
            function=lambda limit=20: context_builder.email.get_unread_emails(limit=limit),
            parameters={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of emails to fetch (default: 20)"
                    }
                },
                "required": []
            },
            requires_integration="email"
        ))

        registry.register(Tool(
            name="search_emails",
            description="Search emails by query",
            function=lambda query, limit=20: context_builder.email.search_emails(
                query=query, limit=limit
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of emails to fetch (default: 20)"
                    }
                },
                "required": ["query"]
            },
            requires_integration="email"
        ))

    return registry
