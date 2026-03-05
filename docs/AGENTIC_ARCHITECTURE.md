# Agentic Architecture Deep Dive

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER (You)                              │
│                   Browser / Chat Interface                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ "What's on my todo list?"
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Server (main.py)                     │
│                                                                  │
│  POST /api/ask                                                  │
│    ├─ Request: {"question": "...", "include_context": true}    │
│    └─ Response: {"answer": "..."}                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ assistant.answer_question_agentic()
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              PersonalAssistant (assistant.py)                   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  Agentic Loop (max 5 iterations)                       │   │
│  │                                                          │   │
│  │  1. Build prompt with:                                  │   │
│  │     - System rules (system_prompts.py)                  │   │
│  │     - Tool documentation (tools.tools_to_prompt())      │   │
│  │     - Conversation history                              │   │
│  │     - User question                                     │   │
│  │                                                          │   │
│  │  2. Call LLM (qwen2.5:14b via Ollama)                  │   │
│  │                                                          │   │
│  │  3. Parse response:                                     │   │
│  │     ├─ Tool call? → Execute tool                        │   │
│  │     └─ Final answer? → Return to user                   │   │
│  │                                                          │   │
│  │  4. If tool call:                                       │   │
│  │     - Execute tool via ToolRegistry                     │   │
│  │     - Get result (success/failure)                      │   │
│  │     - Feed result back to LLM                           │   │
│  │     - Log action                                        │   │
│  │     - Loop again (step 2)                               │   │
│  └────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ Tool calls
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ToolRegistry (tools.py)                       │
│                                                                  │
│  Available Tools:                                               │
│  ┌──────────────────────────────────────────────────────┐     │
│  │  Calendar Tools (3)                                   │     │
│  │  ├─ get_calendar_events                              │     │
│  │  ├─ get_upcoming_events                              │     │
│  │  └─ create_calendar_event                            │     │
│  └──────────────────────────────────────────────────────┘     │
│  ┌──────────────────────────────────────────────────────┐     │
│  │  Notion Tools (3) - READ ONLY                        │     │
│  │  ├─ search_notion              ← Exposed ✅         │     │
│  │  ├─ get_recent_notion_updates  ← Exposed ✅         │     │
│  │  └─ get_notion_page_content    ← Exposed ✅         │     │
│  └──────────────────────────────────────────────────────┘     │
│  ┌──────────────────────────────────────────────────────┐     │
│  │  Email Tools (2)                                     │     │
│  │  ├─ get_unread_emails                                │     │
│  │  └─ search_emails                                    │     │
│  └──────────────────────────────────────────────────────┘     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ Calls underlying integrations
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                Integrations (integrations/*.py)                 │
│                                                                  │
│  ┌─────────────────────┐  ┌─────────────────────┐             │
│  │ GoogleCalendarInt.  │  │  NotionIntegration  │             │
│  │                     │  │                     │             │
│  │ Methods:            │  │ Exposed Methods:    │             │
│  │ • authenticate()    │  │ • search_pages()    │             │
│  │ • get_events()      │  │ • get_page_content()│             │
│  │ • create_event()    │  │ • get_recent_...()  │             │
│  └─────────────────────┘  │                     │             │
│                            │ Hidden Methods:     │             │
│  ┌─────────────────────┐  │ • get_database_...()│ ← NOT EXPOSED❌│
│  │  EmailIntegration   │  │   (exists but not   │             │
│  │                     │  │    in ToolRegistry) │             │
│  │ Methods:            │  │                     │             │
│  │ • get_unread()      │  │ Write Methods:      │             │
│  │ • search_emails()   │  │ • create_page()     │ ← NOT IMPL ❌│
│  │ • mark_as_read()    │  │ • update_page()     │ ← NOT IMPL ❌│
│  └─────────────────────┘  │ • append_blocks()   │ ← NOT IMPL ❌│
│                            │ • update_todo()     │ ← NOT IMPL ❌│
│                            └─────────────────────┘             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ API Calls
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    External Services                            │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Ollama     │  │    Notion    │  │    Gmail     │         │
│  │              │  │     API      │  │     IMAP     │         │
│  │ qwen2.5:14b  │  │              │  │              │         │
│  │ (localhost)  │  │  (REST API)  │  │   (Email)    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Example: "What's on my todo list?"

### Step-by-Step Execution

```
1. USER TYPES
   │
   ├─ Message: "What's on my todo list?"
   │
   ▼

2. FASTAPI RECEIVES REQUEST
   │
   ├─ POST /api/ask
   ├─ Body: {"question": "What's on my todo list?", "include_context": true}
   │
   ▼

3. ASSISTANT BUILDS PROMPT
   │
   ├─ System Prompt:
   │   "You are a Personal Assistant AI..."
   │   "STRICT RULES..."
   │   "NEVER HALLUCINATE..."
   │
   ├─ Tools Prompt:
   │   "## AVAILABLE TOOLS"
   │   "### search_notion"
   │   "### get_recent_notion_updates"
   │   "### get_notion_page_content"
   │
   ├─ User Message:
   │   "What's on my todo list?"
   │
   ▼

4. LLM RECEIVES PROMPT (via Ollama)
   │
   ├─ Model: qwen2.5:14b
   ├─ Temperature: 0.3 (low = more factual)
   ├─ Context: Full system prompt + tools + user message
   │
   ▼

5. LLM RESPONDS - ITERATION 1
   │
   ├─ Response:
   │   ```json
   │   {
   │     "thought": "User wants their todo list. I should search for pages with 'todo' or 'tasks'",
   │     "tool": "search_notion",
   │     "parameters": {"query": "todo"}
   │   }
   │   ```
   │
   ▼

6. ASSISTANT EXTRACTS TOOL CALL
   │
   ├─ Tool name: "search_notion"
   ├─ Parameters: {"query": "todo"}
   │
   ▼

7. TOOL REGISTRY EXECUTES
   │
   ├─ registry.get_tool("search_notion")
   ├─ tool.execute(query="todo")
   │
   ▼

8. NOTION INTEGRATION CALLED
   │
   ├─ notion.search_pages(query="todo")
   ├─ Notion API: POST https://api.notion.com/v1/search
   │
   ▼

9. NOTION API RETURNS
   │
   ├─ Response:
   │   [
   │     {
   │       "id": "2eea77fe03f78098a233c3c016f0d857",
   │       "title": "Tasks",
   │       "url": "https://notion.so/Tasks-...",
   │       "last_edited_time": "2026-03-05T09:30:00.000Z"
   │     }
   │   ]
   │
   ▼

10. RESULT FED BACK TO LLM
    │
    ├─ Message: "✅ Tool 'search_notion' executed successfully.
    │            Result: [{"id": "2eea...", "title": "Tasks", ...}]"
    │
    ▼

11. LLM RECEIVES RESULT - ITERATION 2
    │
    ├─ LLM thinks: "Found a page called 'Tasks'. Need to read its content."
    │
    ├─ Response:
    │   ```json
    │   {
    │     "thought": "Found Tasks page. Now get its content to see actual todos",
    │     "tool": "get_notion_page_content",
    │     "parameters": {"page_id": "2eea77fe03f78098a233c3c016f0d857"}
    │   }
    │   ```
    │
    ▼

12. TOOL REGISTRY EXECUTES AGAIN
    │
    ├─ registry.get_tool("get_notion_page_content")
    ├─ tool.execute(page_id="2eea77fe03f78098a233c3c016f0d857")
    │
    ▼

13. NOTION INTEGRATION CALLED AGAIN
    │
    ├─ notion.get_page_content(page_id="2eea...")
    ├─ Notion API: GET https://api.notion.com/v1/pages/2eea...
    ├─ Notion API: GET https://api.notion.com/v1/blocks/2eea.../children
    ├─ Recursively fetch nested blocks
    │
    ▼

14. NOTION API RETURNS CONTENT
    │
    ├─ Response:
    │   {
    │     "metadata": {"title": "Tasks", ...},
    │     "content": "## Tasks\n[ ] Buy groceries\n[x] Finish report\n[ ] Call dentist"
    │   }
    │
    ▼

15. RESULT FED BACK TO LLM
    │
    ├─ Message: "✅ Tool 'get_notion_page_content' executed successfully.
    │            Result: {metadata: {...}, content: '## Tasks\n[ ] Buy...'}"
    │
    ▼

16. LLM RECEIVES CONTENT - ITERATION 3
    │
    ├─ LLM thinks: "I have the full content now. Can present to user."
    │
    ├─ Response (NO JSON, just text):
    │   "Here's your todo list:
    │
    │    ## Tasks
    │
    │    Incomplete:
    │    - [ ] Buy groceries
    │    - [ ] Call dentist
    │
    │    Completed:
    │    - [x] Finish report
    │
    │    You have 2 tasks remaining."
    │
    ▼

17. ASSISTANT DETECTS FINAL ANSWER
    │
    ├─ No JSON tool call found
    ├─ Return response as final answer
    │
    ▼

18. FASTAPI RETURNS TO USER
    │
    ├─ Response: {"answer": "Here's your todo list: ..."}
    │
    ▼

19. BROWSER DISPLAYS
    │
    ├─ Chat interface shows assistant message
    ├─ Action log shows:
    │   ✅ Called search_notion
    │   ✅ Called get_notion_page_content
    │
    ▼

20. USER SEES RESULT ✅
```

---

## Tool Registry Architecture

### How Tools Are Registered

```python
# src/core/tools.py, line 165-334

def create_tool_registry(context_builder) -> ToolRegistry:
    """
    This function is called ONCE at startup.
    It inspects which integrations are available and
    registers appropriate tools.
    """
    registry = ToolRegistry()

    # Check if Notion is configured
    if context_builder.notion:
        # Create async wrapper (important!)
        async def search_notion_wrapper(query):
            return await context_builder.notion.search_pages(query)

        # Register the tool
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

    # Similar for other tools...

    return registry
```

### Tool Execution Flow

```python
# When LLM calls a tool:

1. EXTRACT TOOL CALL
   tool_call = {
       "tool": "search_notion",
       "parameters": {"query": "todo"}
   }

2. GET TOOL FROM REGISTRY
   tool = registry.get_tool("search_notion")
   # tool.function = search_notion_wrapper

3. EXECUTE TOOL
   result = await tool.execute(**parameters)
   # Internally calls: await search_notion_wrapper(query="todo")
   #                   └─ await notion.search_pages(query="todo")
   #                      └─ await client.search(query="todo")
   #                         └─ HTTP POST to Notion API

4. RETURN RESULT
   {
       "success": True,
       "result": [...page data...],
       "error": None
   }
```

---

## Missing Capabilities Diagram

### What EXISTS vs What's EXPOSED

```
┌─────────────────────────────────────────────────────────────┐
│            NotionIntegration Class                          │
│         (src/integrations/notion.py)                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  READ METHODS (Implemented & Exposed ✅)                    │
│  ┌────────────────────────────────────────────┐            │
│  │ • search_pages()          → Tool: search_notion         │
│  │ • get_page_content()      → Tool: get_notion_page_...   │
│  │ • get_recent_updates()    → Tool: get_recent_notion_... │
│  └────────────────────────────────────────────┘            │
│                                                              │
│  READ METHODS (Implemented but NOT Exposed ❌)              │
│  ┌────────────────────────────────────────────┐            │
│  │ • get_database_entries()  → NO TOOL! ❌                │
│  │   (Can query databases with filters)                    │
│  │   EXISTS at line 53-83                                  │
│  │   Could be very useful for structured data              │
│  └────────────────────────────────────────────┘            │
│                                                              │
│  WRITE METHODS (NOT Implemented ❌)                         │
│  ┌────────────────────────────────────────────┐            │
│  │ • create_page()           → NOT IMPL ❌                │
│  │ • update_page_content()   → NOT IMPL ❌                │
│  │ • append_blocks()         → NOT IMPL ❌                │
│  │ • update_todo_checkbox()  → NOT IMPL ❌                │
│  │ • delete_page()           → NOT IMPL ❌                │
│  │ • update_properties()     → NOT IMPL ❌                │
│  └────────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

### Impact on Agent Capabilities

```
CURRENT STATE (Read-Only):
User: "What's on my todo list?"
Agent: ✅ Can answer (reads page content)

User: "Add 'buy milk' to my todo list"
Agent: ❌ Cannot do (no create_page or append_blocks tool)

User: "Mark 'buy groceries' as done"
Agent: ❌ Cannot do (no update_todo tool)

User: "Show me all tasks with status 'In Progress'"
Agent: ❌ Cannot do efficiently (get_database_entries not exposed)

User: "Create a note about today's meeting"
Agent: ❌ Cannot do (no create_page tool)
```

---

## What Makes an Agent "Truly Agentic"?

### Current State: **Semi-Agentic** ⚠️

✅ **Has**:
- Multi-turn tool calling (can chain multiple tools)
- Smart decision making (knows when to use which tool)
- Transparent actions (logs everything)
- Graceful degradation (works with partial integrations)

❌ **Missing**:
- Write operations (can't modify data)
- Proactive suggestions (can't say "you should...")
- Task persistence (no memory between sessions)
- Complex workflows (limited to 5 tool calls)

### Goal State: **Fully Agentic** 🎯

✅ **Would Have**:
- Read AND write operations
- Can manage your tasks autonomously
- Can create reminders and notes
- Can learn your patterns
- Can suggest next actions
- Persistent memory across sessions

---

## How to Make It Fully Agentic

### Phase 1: Expose Existing Function ✅ EASY
```python
# In src/core/tools.py, add:

async def get_database_entries_wrapper(database_id=None, filter_dict=None):
    return await context_builder.notion.get_database_entries(
        database_id=database_id,
        filter_dict=filter_dict
    )

registry.register(Tool(
    name="query_notion_database",
    description="Query a Notion database with optional filters",
    function=get_database_entries_wrapper,
    parameters={...},
    requires_integration="notion"
))
```

### Phase 2: Implement Write Operations ⚙️ MEDIUM
```python
# In src/integrations/notion.py, add:

async def create_page(
    self,
    parent_id: str,
    title: str,
    content_blocks: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Create a new Notion page"""
    response = await self.client.pages.create(
        parent={"page_id": parent_id},
        properties={
            "title": [{"text": {"content": title}}]
        },
        children=content_blocks
    )
    return response

async def update_todo_status(
    self,
    block_id: str,
    checked: bool
) -> Dict[str, Any]:
    """Check/uncheck a todo item"""
    response = await self.client.blocks.update(
        block_id=block_id,
        to_do={"checked": checked}
    )
    return response
```

### Phase 3: Add to Tool Registry 🔧 EASY
```python
# Register new tools in create_tool_registry()

registry.register(Tool(
    name="create_notion_page",
    description="Create a new page in Notion",
    ...
))

registry.register(Tool(
    name="update_todo_status",
    description="Mark a todo item as complete or incomplete",
    ...
))
```

---

## Performance Considerations

### Current Bottlenecks

1. **Sequential Tool Calls**
   - LLM calls one tool at a time
   - Can't parallelize (e.g., check calendar AND emails simultaneously)
   - Solution: Implement parallel tool execution

2. **Recursive Block Fetching**
   - `get_page_content()` makes multiple API calls for nested blocks
   - Can be slow for deeply nested pages
   - Solution: Caching or pagination

3. **No Result Caching**
   - Same search repeated = same API call
   - Wastes tokens and time
   - Solution: Redis or in-memory cache (TTL 5 minutes)

4. **Token Usage**
   - Every tool call adds ~500-1000 tokens to conversation
   - Max 5 iterations = up to 5000 tokens
   - Solution: Summarize old tool results

---

## Summary

### What You Have:
1. ✅ **Clear tool documentation** - LLM knows exactly what tools exist
2. ✅ **Proper architecture** - ToolRegistry → Integrations → APIs
3. ✅ **Agentic loop** - LLM can chain multiple tools intelligently
4. ✅ **Anti-hallucination** - Strong safeguards prevent making up data
5. ✅ **Action logging** - Full transparency of what agent does

### What's Missing:
1. ❌ **Write operations** - Can't create/update/delete Notion content
2. ❌ **Exposed database queries** - `get_database_entries()` exists but not usable
3. ❌ **Task management** - Can't check off todos or update status
4. ❌ **Proactive capabilities** - Can only react to questions, not suggest actions

### To Make Fully Agentic:
1. 🔧 Expose `get_database_entries()` as tool (10 minutes)
2. 🔨 Implement write operations (1-2 hours)
3. 🎯 Add proactive suggestions (requires prompt engineering)
4. 💾 Add session persistence (requires database)

**Your agent is smart and well-documented, but read-only.**
**Add write operations = unlock 80% more usefulness.**
