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

**Example 1 - Simple Query**:
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

**Example 2 - Task Prioritization** (IMPORTANT):
User: "What should I prioritize?" or "Prioritize my tasks"
You should:
1. First search for todo/task pages: search_notion with query="todo" or "tasks"
2. Then get the content of those pages: get_notion_page_content
3. Analyze the todos and prioritize based on urgency, importance, deadlines

```json
{
  "thought": "User wants task prioritization. First, I need to find their todo list in Notion",
  "tool": "search_notion",
  "parameters": {
    "query": "todo"
  }
}
```

After getting the page, continue:
```json
{
  "thought": "Found the todo page. Now I need to read its content to see all tasks",
  "tool": "get_notion_page_content",
  "parameters": {
    "page_id": "page_id_from_search_result"
  }
}
```

Then analyze and present priorities to the user.

**Example 3 - Learning/Tutorial Requests** (IMPORTANT):
User: "Help me learn guitar chords for [song]" or "How to [do something]"
You should:
1. Use search_and_fetch (NOT just search_web) to get actual content
2. Fetch from 2-3 sources for comprehensive info
3. If first attempt doesn't work, try simpler/broader search terms

```json
{
  "thought": "User wants to learn guitar chords. I'll use search_and_fetch to get detailed content with chords.",
  "tool": "search_and_fetch",
  "parameters": {
    "query": "Give Me Some Sunshine guitar chords tabs tutorial",
    "num_results": 3
  }
}
```

If the content doesn't have what you need, try a different approach:
```json
{
  "thought": "First search didn't have chords. Let me try a more specific search.",
  "tool": "search_and_fetch",
  "parameters": {
    "query": "Give Me Some Sunshine 3 Idiots guitar chords PDF",
    "num_results": 2
  }
}
```

**TOOL SELECTION GUIDE**:
- **search_web**: Quick search for links/snippets (weather, news, simple queries)
- **search_and_fetch**: Deep content retrieval (tutorials, articles, how-tos)
- **fetch_webpage**: When you have a specific URL to read
- **get_weather**: Dedicated weather tool (faster than search)
- **get_news**: Dedicated news tool (better than search)

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

    # Web search tools
    if context_builder.web_search:
        def search_web_wrapper(query, num_results=5):
            return context_builder.web_search.search_google(query, num_results)

        def fetch_webpage_wrapper(url):
            return context_builder.web_search.fetch_webpage(url)

        def search_and_fetch_wrapper(query, num_results=3):
            return context_builder.web_search.search_and_fetch(query, num_results)

        def get_weather_wrapper(location):
            return context_builder.web_search.get_weather(location)

        def get_news_wrapper(topic="latest news", num_results=5):
            return context_builder.web_search.get_news(topic, num_results)

        registry.register(Tool(
            name="search_web",
            description="Search the internet using Google to find current information, facts, news, or answers",
            function=search_web_wrapper,
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "num_results": {
                        "type": "integer",
                        "description": "Number of results to return (default: 5, max: 10)"
                    }
                },
                "required": ["query"]
            },
            requires_integration="web_search"
        ))

        registry.register(Tool(
            name="fetch_webpage",
            description="Fetch and extract text content from a specific webpage URL",
            function=fetch_webpage_wrapper,
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full URL of the webpage to fetch"}
                },
                "required": ["url"]
            },
            requires_integration="web_search"
        ))

        registry.register(Tool(
            name="search_and_fetch",
            description="Search Google and automatically fetch full content from top results (combines search + fetch)",
            function=search_and_fetch_wrapper,
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "num_results": {
                        "type": "integer",
                        "description": "Number of results to fetch (default: 3, max: 5)"
                    }
                },
                "required": ["query"]
            },
            requires_integration="web_search"
        ))

        registry.register(Tool(
            name="get_weather",
            description="Get current weather information for any location",
            function=get_weather_wrapper,
            parameters={
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name or location (e.g., 'Tokyo', 'New York')"}
                },
                "required": ["location"]
            },
            requires_integration="web_search"
        ))

        registry.register(Tool(
            name="get_news",
            description="Get latest news articles about a specific topic",
            function=get_news_wrapper,
            parameters={
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "News topic (default: 'latest news')"},
                    "num_results": {
                        "type": "integer",
                        "description": "Number of news articles (default: 5)"
                    }
                },
                "required": []
            },
            requires_integration="web_search"
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
