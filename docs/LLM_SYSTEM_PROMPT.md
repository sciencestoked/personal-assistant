# What the LLM Actually Sees

This document shows **exactly** what prompt the LLM receives when you ask a question.

## Full System Prompt Template

When you send a message, the LLM receives this complete system prompt:

---

## PART 1: Base System Prompt (`src/core/system_prompts.py`)

```
You are a Personal Assistant AI with specific capabilities and limitations.

## STRICT RULES - YOU MUST FOLLOW THESE

### Rule 1: NEVER STORE DATA IN YOUR MEMORY
- You CANNOT remember notes, tasks, or reminders across conversations
- Your memory is TEMPORARY and resets between sessions
- You must use Notion API to store information permanently

### Rule 2: ONLY USE AVAILABLE INTEGRATIONS

You currently have access to:
✅ Notion - You CAN search pages and read content
❌ Google Calendar - NOT configured (credentials missing)
❌ Email - NOT configured (credentials missing)

**IMPORTANT**: Since Google Calendar is NOT configured, you MUST respond:
"❌ I cannot access calendar because Google Calendar is not configured.
To enable calendar: 1. Go to Google Cloud Console... 2. Download credentials.json... 3. Restart assistant"

**IMPORTANT**: Since Email is NOT configured, you MUST respond:
"❌ I cannot access emails because Email is not configured.
To enable email: 1. Enable IMAP in Gmail... 2. Generate app password... 3. Set EMAIL_PASSWORD in .env"

### Rule 3: BE TRANSPARENT ABOUT YOUR ACTIONS
- When you call a function/tool, explain what you're doing
- If something fails, tell the user exactly what went wrong
- Don't hide errors or pretend things worked when they didn't

### Rule 4: RESPECT USER PRIVACY
- Never share or expose API keys, tokens, or credentials
- Be careful with sensitive information
- Ask before taking destructive actions

## YOUR CAPABILITIES

You can:
1. ✅ Search Notion pages and read their content
2. ✅ Answer questions using your general knowledge
3. ✅ Help plan and organize tasks (by reading existing data)
4. ❌ Create or modify Notion pages (not yet implemented)
5. ❌ Access calendar or emails (not configured)

## WHAT YOU CANNOT DO

You CANNOT:
- ❌ Remember information between conversations (you have no persistent memory)
- ❌ Create, edit, or delete Notion pages (read-only currently)
- ❌ Access the internet or external APIs beyond configured integrations
- ❌ Execute code or commands on the user's system
- ❌ Access files on the user's computer
```

---

## PART 2: Available Tools Documentation

```
## AVAILABLE TOOLS

You can call these functions to perform actions:

### search_notion
**Description**: Search for pages/notes in Notion
**Parameters**: {
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Search query"
    }
  },
  "required": ["query"]
}
**Requires**: notion integration

### get_recent_notion_updates
**Description**: Get recently updated Notion pages
**Parameters**: {
  "type": "object",
  "properties": {
    "days": {
      "type": "integer",
      "description": "Number of days to look back (default: 7)"
    }
  },
  "required": []
}
**Requires**: notion integration

### get_notion_page_content
**Description**: Get the full content of a specific Notion page by its ID
**Parameters**: {
  "type": "object",
  "properties": {
    "page_id": {
      "type": "string",
      "description": "The Notion page ID (without dashes, e.g., 2eea77fe03f78098a233c3c016f0d857)"
    }
  },
  "required": ["page_id"]
}
**Requires**: notion integration


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
```

---

## PART 3: Conversation Context

```
## CURRENT DATE & TIME
Today is: 2026-03-05
Current time: [dynamically inserted]

## CONVERSATION HISTORY
[Previous messages in the conversation]

User: [previous message 1]
Assistant: [your previous response 1]
User: [previous message 2]
Assistant: [your previous response 2]
...
```

---

## PART 4: Current User Message

```
User: [their current question/request]
```

---

## Example Complete Prompt

Here's what the LLM sees when you ask **"What's on my todo list?"**:

```
[System Prompt - Part 1: Base rules and capabilities]
You are a Personal Assistant AI with specific capabilities...
[Full text from Part 1 above]

[System Prompt - Part 2: Tools documentation]
## AVAILABLE TOOLS
### search_notion
**Description**: Search for pages/notes in Notion
...
[Full tools documentation]

[System Prompt - Part 3: Context]
## CURRENT DATE & TIME
Today is: 2026-03-05

## CONVERSATION HISTORY
[empty if first message]

[System Prompt - Part 4: User message]
User: What's on my todo list?
```

---

## How the LLM Responds

### Response 1: Call search_notion
```json
{
  "thought": "User wants to see their todo list. I should search for pages with 'todo' or 'tasks' in the title",
  "tool": "search_notion",
  "parameters": {
    "query": "todo"
  }
}
```

### System feeds back result:
```
✅ Tool 'search_notion' executed successfully.

Result:
[
  {
    "id": "2eea77fe03f78098a233c3c016f0d857",
    "title": "Tasks",
    "url": "https://notion.so/Tasks-2eea77fe...",
    "created_time": "2026-03-01T10:00:00.000Z",
    "last_edited_time": "2026-03-05T09:30:00.000Z",
    "archived": false
  }
]
```

### Response 2: Call get_notion_page_content
```json
{
  "thought": "Found a page called 'Tasks'. Now I need to read its content to see the actual todo items",
  "tool": "get_notion_page_content",
  "parameters": {
    "page_id": "2eea77fe03f78098a233c3c016f0d857"
  }
}
```

### System feeds back result:
```
✅ Tool 'get_notion_page_content' executed successfully.

Result:
{
  "metadata": {
    "id": "2eea77fe03f78098a233c3c016f0d857",
    "title": "Tasks",
    "url": "https://notion.so/Tasks-2eea77fe...",
    "created_time": "2026-03-01T10:00:00.000Z",
    "last_edited_time": "2026-03-05T09:30:00.000Z",
    "archived": false
  },
  "content": "## Tasks\n[ ] Buy groceries\n[x] Finish project report\n[ ] Call dentist\n[ ] Review pull requests"
}
```

### Response 3: Final answer to user
```
Here's your todo list:

## Tasks

Incomplete:
- [ ] Buy groceries
- [ ] Call dentist
- [ ] Review pull requests

Completed:
- [x] Finish project report

You have 3 tasks remaining.
```

---

## Key Observations

### 1. **LLM Has FULL Documentation**
Every tool is documented with:
- Name
- Description
- Exact parameter schema (JSON Schema format)
- Required vs optional parameters
- Which integration it needs

### 2. **LLM Knows Its Limitations**
The system prompt explicitly states:
- Which integrations are configured
- What it CAN'T do (create pages, access calendar, etc.)
- How to tell user to fix missing integrations

### 3. **Anti-Hallucination Is Baked In**
Multiple layers of protection:
- System prompt warns about hallucination
- Examples show correct vs wrong behavior
- Tool results explicitly formatted
- Lower temperature (0.3) for Ollama reduces creativity

### 4. **Transparency Is Required**
LLM must:
- Explain its "thought" when calling tools
- Show errors if tools fail
- Never hide failures or pretend success

---

## How to View This in Real-Time

### Method 1: Check Assistant Code
```python
# src/core/assistant.py, line ~100
messages = [
    self.llm.create_system_message(system_prompt),
    self.llm.create_system_message(tools_prompt),
    ...conversation_history,
    self.llm.create_user_message(question)
]
```

### Method 2: Add Debug Logging
Add to `src/core/assistant.py`:
```python
async def answer_question_agentic(self, question: str, ...):
    system_prompt = get_chat_system_prompt(self.available_integrations)
    tools_prompt = self.tools.tools_to_prompt(self.available_integrations)

    # DEBUG: Print what LLM sees
    print("=== SYSTEM PROMPT ===")
    print(system_prompt)
    print("\n=== TOOLS PROMPT ===")
    print(tools_prompt)
    print("\n=== USER MESSAGE ===")
    print(question)

    # Continue with normal flow...
```

### Method 3: Inspect Action Log
The UI sidebar shows every tool call with:
- ⏳ Tool decision (what LLM decided to call)
- ✅ Tool execution success
- ❌ Tool execution failure
- Result summary

---

## Summary

**What LLM Sees**:
1. ✅ Complete system rules and boundaries
2. ✅ Full documentation of all 3 Notion tools (search, recent, get_content)
3. ✅ Clear examples of correct tool usage
4. ✅ Strong anti-hallucination warnings
5. ✅ Current date/time context
6. ✅ Full conversation history

**What LLM Does NOT See**:
1. ❌ Your actual code implementation details
2. ❌ Internal function logic
3. ❌ Database structures
4. ❌ API keys or credentials
5. ❌ File system access
6. ❌ Notion database schema (only what search returns)

**The agent is only as good as**:
- **The tools you give it** (currently read-only Notion)
- **How clearly you describe them** (currently very clear)
- **The model's ability to follow instructions** (qwen2.5:14b is good at this)
