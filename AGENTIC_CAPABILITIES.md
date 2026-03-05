# Agentic Capabilities Documentation

This document describes all the tools/functions available to the Personal Assistant LLM and how they work.

## Overview

The assistant uses an **agentic tool-calling architecture**:
1. User asks a question
2. LLM analyzes what data it needs
3. LLM calls tools (functions) to get that data
4. LLM receives results and decides next action
5. LLM can call multiple tools in sequence (max 5 iterations)
6. LLM provides final answer to user

## Architecture Components

### Tool Registry (`src/core/tools.py`)
- **ToolRegistry**: Central registry of all available tools
- **Tool**: Represents a single callable function with:
  - `name`: Identifier for the tool
  - `description`: What it does (shown to LLM)
  - `function`: The actual Python function
  - `parameters`: JSON Schema describing expected inputs
  - `requires_integration`: Which service it needs (calendar/notion/email)

### How LLM Sees Tools

When the LLM receives a question, it gets a system prompt with:
```markdown
## AVAILABLE TOOLS

### tool_name
**Description**: What this tool does
**Parameters**: {JSON Schema}
**Requires**: integration_name
```

The LLM then responds with JSON to call a tool:
```json
{
  "thought": "Why I'm calling this",
  "tool": "tool_name",
  "parameters": {"param1": "value1"}
}
```

## Currently Available Tools

### 📅 Calendar Tools (3 tools)

#### `get_calendar_events`
- **Purpose**: Get events for a specific date
- **Parameters**:
  - `date` (required): Date in YYYY-MM-DD format
- **Returns**: List of events with title, start, end, location, description
- **Example Use**: "What's on my calendar tomorrow?"

#### `get_upcoming_events`
- **Purpose**: Get events for the next N days
- **Parameters**:
  - `days` (optional): Number of days to look ahead (default: 7)
- **Returns**: List of upcoming events sorted by date
- **Example Use**: "What's coming up this week?"

#### `create_calendar_event`
- **Purpose**: Create a new calendar event
- **Parameters**:
  - `summary` (required): Event title
  - `start_time` (required): ISO format datetime
  - `end_time` (required): ISO format datetime
  - `description` (optional): Event details
  - `location` (optional): Event location
- **Returns**: Created event details
- **Example Use**: "Schedule a meeting with John tomorrow at 2pm"

---

### 📝 Notion Tools (3 tools - INCOMPLETE)

#### `search_notion`
- **Purpose**: Search for pages/notes in Notion by keyword
- **Parameters**:
  - `query` (required): Search query string
- **Returns**: List of matching pages with id, title, url, timestamps
- **Example Use**: "Find my notes about Python"
- **Limitations**: Only returns page metadata, not content

#### `get_recent_notion_updates`
- **Purpose**: Get recently edited Notion pages
- **Parameters**:
  - `days` (optional): Number of days to look back (default: 7)
- **Returns**: List of recently updated pages sorted by last_edited_time
- **Example Use**: "What notes did I update this week?"
- **Limitations**: Only returns metadata, not content

#### `get_notion_page_content`
- **Purpose**: Get full content of a specific Notion page
- **Parameters**:
  - `page_id` (required): Notion page ID (without dashes)
- **Returns**:
  - `metadata`: Page title, url, timestamps
  - `content`: Full page content including:
    - Paragraphs, headings (h1, h2, h3)
    - Bulleted lists, numbered lists
    - **Todo items with [x] checked and [ ] unchecked**
    - Code blocks, quotes, dividers
    - **Nested blocks (recursively extracted)**
- **Example Use**: "What's on my todo list?"
- **How to get page_id**: Use `search_notion` first, then extract `id` field
- **Note**: This is the ONLY tool that reads actual page content

---

### 📧 Email Tools (2 tools)

#### `get_unread_emails`
- **Purpose**: Get unread emails from inbox
- **Parameters**:
  - `limit` (optional): Max number of emails (default: 20)
- **Returns**: List of unread emails with subject, sender, date, preview
- **Example Use**: "Do I have any unread emails?"

#### `search_emails`
- **Purpose**: Search emails by query
- **Parameters**:
  - `query` (required): Search query
  - `limit` (optional): Max number of emails (default: 20)
- **Returns**: List of matching emails
- **Example Use**: "Find emails from John about the project"

---

## Missing Capabilities (Not Yet Implemented)

### 🚫 Notion Write Operations (HIGH PRIORITY)

These are **critical for a true personal assistant** but NOT yet implemented:

1. **`create_notion_page()`** - Create new notes/pages
   - Use case: "Create a note about today's meeting"
   - Status: ❌ Not implemented
   - Impact: Can't save information

2. **`update_todo_status()`** - Check/uncheck todo items
   - Use case: "Mark 'buy groceries' as done"
   - Status: ❌ Not implemented
   - Impact: Can't manage tasks

3. **`append_to_page()`** - Add content to existing pages
   - Use case: "Add this to my meeting notes"
   - Status: ❌ Not implemented
   - Impact: Can't update existing notes

4. **`archive_page()`** - Archive completed tasks
   - Use case: "Archive completed tasks"
   - Status: ❌ Not implemented
   - Impact: Can't clean up workspace

### 🚫 Notion Database Operations (MEDIUM PRIORITY)

5. **`get_database_entries()`** - Query databases with filters
   - Use case: "Show me all tasks with status 'In Progress'"
   - Status: ⚠️ **EXISTS in code but NOT exposed as tool!**
   - Location: `src/integrations/notion.py:53`
   - Impact: Can't use structured databases effectively

6. **`query_database_with_filter()`** - Advanced filtering
   - Use case: "Show urgent tasks due this week"
   - Status: ❌ Not implemented
   - Impact: Can't do smart task queries

7. **`get_page_properties()`** - Get metadata (tags, status, dates)
   - Use case: "What's the status of this project?"
   - Status: ❌ Not implemented
   - Impact: Can't read structured properties

### 🚫 Notion Advanced Features (LOW PRIORITY)

8. **`update_page_properties()`** - Change tags, status, etc.
   - Use case: "Change task status to 'Done'"
   - Status: ❌ Not implemented

9. **`get_page_backlinks()`** - Find pages linking to this one
   - Use case: "What pages reference this project?"
   - Status: ❌ Not implemented

---

## How Tool Calling Works

### Code Flow

1. **User asks question** → `POST /api/ask` → `assistant.answer_question_agentic()`

2. **LLM receives prompt** with:
   - System prompt (rules, boundaries)
   - Tools documentation (`tools_to_prompt()`)
   - Conversation history
   - User's question

3. **LLM responds** with either:
   - **Tool call**: JSON with `tool`, `parameters`, `thought`
   - **Final answer**: Direct text response

4. **Tool execution**:
   ```python
   tool = registry.get_tool(tool_name)
   result = await tool.execute(**parameters)
   ```

5. **Result fed back to LLM**:
   ```
   ✅ Tool 'search_notion' executed successfully.
   Result: [{"id": "123", "title": "My Notes"}]
   ```

6. **LLM decides**:
   - Call another tool? (e.g., `get_notion_page_content` with that ID)
   - Provide final answer? (present results to user)

7. **Max 5 iterations** to prevent infinite loops

### Example Multi-Tool Sequence

**User**: "What's on my todo list?"

**Iteration 1**:
- LLM calls: `search_notion` with query="todo"
- Result: `[{"id": "2eea77fe03f78098a233c3c016f0d857", "title": "Tasks"}]`

**Iteration 2**:
- LLM calls: `get_notion_page_content` with page_id="2eea77fe03f78098a233c3c016f0d857"
- Result: Full page content with todo items:
  ```
  ## Tasks
  [ ] Buy groceries
  [x] Finish report
  [ ] Call dentist
  ```

**Final Response**:
- LLM presents: "Here's your todo list: ..."

---

## Anti-Hallucination Measures

The system has **strict rules** to prevent the LLM from making up data:

### 1. System Prompts (`src/core/system_prompts.py`)
```
STRICT RULES:
1. NEVER STORE DATA IN YOUR MEMORY
2. ONLY USE AVAILABLE INTEGRATIONS
3. NEVER HALLUCINATE TOOL RESULTS
```

### 2. Tool Result Validation
Every tool call shows:
```
⚠️ ONLY show data that was explicitly in the tool result JSON.
⚠️ If the result is empty or null, say so - don't invent content.
```

### 3. Temperature Control
- Ollama: `temperature=0.3` (less creative, more factual)
- Cloud APIs: `temperature=0.7` (balanced)

### 4. Action Logging
Every tool call is logged with:
- Timestamp
- Action type
- Success/failure status
- Result summary

Visible in UI sidebar and `assistant.action_log`

---

## Limitations

### Current Constraints:

1. **Read-Only Notion**: Can only READ, cannot CREATE or UPDATE
2. **No Database Queries**: Can search pages but not query databases (even though function exists!)
3. **No Task Management**: Can read todos but can't check them off
4. **No Context Persistence**: Conversation resets when server restarts
5. **Max 5 Tool Calls**: Prevents infinite loops but limits complex workflows
6. **Single Tool at a Time**: Can't call multiple tools in parallel

### Why These Limitations Exist:

- **Safety**: Write operations not implemented to prevent accidental data changes
- **Simplicity**: MVP focused on read operations first
- **Testing**: Easier to test and debug read-only operations

---

## Future Enhancements

### Phase 1: Write Operations (Next Priority)
- [ ] Implement `create_notion_page()`
- [ ] Implement `append_to_page()`
- [ ] Implement `update_todo_status()`
- [ ] Expose existing `get_database_entries()` as tool

### Phase 2: Database Operations
- [ ] Implement `query_database_with_filter()`
- [ ] Implement `get_page_properties()`
- [ ] Implement `update_page_properties()`

### Phase 3: Advanced Features
- [ ] Parallel tool calling (multiple tools at once)
- [ ] Conversation persistence (save to database)
- [ ] Custom tool creation via config
- [ ] Tool composition (chain tools automatically)

---

## For Developers: Adding New Tools

### Step 1: Implement function in integration
```python
# src/integrations/notion.py
async def create_page(self, parent_id: str, title: str, content: str) -> Dict[str, Any]:
    """Create a new Notion page"""
    # Implementation here
```

### Step 2: Register tool in registry
```python
# src/core/tools.py, in create_tool_registry()
async def create_notion_page_wrapper(parent_id, title, content):
    return await context_builder.notion.create_page(parent_id, title, content)

registry.register(Tool(
    name="create_notion_page",
    description="Create a new Notion page with content",
    function=create_notion_page_wrapper,
    parameters={
        "type": "object",
        "properties": {
            "parent_id": {"type": "string", "description": "Parent page/database ID"},
            "title": {"type": "string", "description": "Page title"},
            "content": {"type": "string", "description": "Page content"}
        },
        "required": ["parent_id", "title", "content"]
    },
    requires_integration="notion"
))
```

### Step 3: Test it
```python
# Chat: "Create a note called 'Test' under my Tasks page"
# LLM should automatically call the new tool
```

---

## Debugging Tools

### View Tool Registry
```python
python3 -c "
from src.core.assistant import assistant
for tool in assistant.tools.get_all_tools():
    print(f'{tool.name}: {tool.description}')
"
```

### View Action Log
```bash
curl http://localhost:8000/api/actions
```

### View Conversation History
```bash
curl http://localhost:8000/api/session/history
```

---

## Summary

**Current State**:
- ✅ 8 tools available (3 calendar, 3 notion, 2 email)
- ✅ Agentic multi-turn tool calling works
- ✅ LLM can see all tools and knows how to use them
- ✅ Anti-hallucination measures in place
- ❌ Read-only Notion (no create/update)
- ❌ Database queries not exposed
- ❌ No task management (can't check off todos)

**Agent Quality = Tool Quality × Documentation Quality**

Your agent is currently:
- **Well-documented** (LLM knows exactly what tools exist)
- **Partially capable** (missing write operations)
- **Smart enough** (qwen2.5:14b follows rules well)

To make it truly useful, **add write operations** (create/update pages, manage todos).
