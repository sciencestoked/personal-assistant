# Personal Assistant - Quick Reference

## Current Agentic Capabilities

### 📊 Statistics
- **Total Tools**: 8 (3 calendar + 3 notion + 2 email)
- **Exposed Notion Functions**: 3 out of 4 available
- **Write Operations**: 0 (read-only)
- **Max Tool Calls**: 5 per conversation turn
- **LLM Model**: qwen2.5:14b (Ollama, local)

---

## Tool Inventory

### ✅ What The Agent CAN Do

| Tool | Purpose | Integration | Status |
|------|---------|-------------|--------|
| `search_notion` | Find pages by keyword | Notion | ✅ Working |
| `get_recent_notion_updates` | See recently edited pages | Notion | ✅ Working |
| `get_notion_page_content` | Read full page with todos | Notion | ✅ Working |
| `get_calendar_events` | Get events for date | Calendar | ⚠️ Not configured |
| `get_upcoming_events` | Get events for next N days | Calendar | ⚠️ Not configured |
| `create_calendar_event` | Create new event | Calendar | ⚠️ Not configured |
| `get_unread_emails` | Get unread emails | Email | ⚠️ Not configured |
| `search_emails` | Search emails by query | Email | ⚠️ Not configured |

### ❌ What The Agent CANNOT Do

| Capability | Why Not | Priority |
|-----------|---------|----------|
| Create Notion pages | Not implemented | 🔴 HIGH |
| Update Notion todos | Not implemented | 🔴 HIGH |
| Query Notion databases | Not exposed (exists in code!) | 🟡 MEDIUM |
| Append to Notion pages | Not implemented | 🔴 HIGH |
| Archive Notion pages | Not implemented | 🟢 LOW |
| Remember past conversations | No persistence | 🟡 MEDIUM |
| Parallel tool calls | Sequential execution only | 🟢 LOW |

---

## Agent Intelligence

### How Smart Is It?

**Model**: qwen2.5:14b (14 billion parameters)
- ✅ Good at following instructions
- ✅ Good at tool selection (knows when to use which tool)
- ✅ Good at chaining tools (search → get content)
- ✅ Low hallucination (temperature 0.3)
- ⚠️ Moderate context window (~32k tokens)
- ❌ No long-term memory

### Anti-Hallucination Measures

1. **System Prompt Rules**: Explicit warnings about making up data
2. **Low Temperature**: 0.3 for Ollama (vs 0.7 for cloud)
3. **Result Validation**: Shows exact tool results to LLM
4. **Examples**: Correct vs wrong behavior in prompt
5. **Action Logging**: Every tool call is recorded

---

## Documentation Files

| File | Purpose | Audience |
|------|---------|----------|
| `AGENTIC_CAPABILITIES.md` | Complete capabilities overview | Developer & User |
| `docs/LLM_SYSTEM_PROMPT.md` | What the LLM actually sees | Developer |
| `docs/AGENTIC_ARCHITECTURE.md` | System architecture deep dive | Developer |
| `QUICK_REFERENCE.md` | This file - quick lookup | Everyone |

---

## Common Use Cases

### ✅ Works Well
- "What's on my todo list?" → Reads Notion todos
- "Show me my recent notes" → Gets recent Notion updates
- "Find my notes about Python" → Searches Notion pages
- "What did I work on yesterday?" → Checks recent updates

### ⚠️ Works Partially
- "Schedule a meeting tomorrow" → Can't create events (calendar not configured)
- "Check my emails" → Can't read emails (email not configured)

### ❌ Doesn't Work Yet
- "Add milk to my shopping list" → Can't write to Notion
- "Mark task as done" → Can't update Notion
- "Create a note about this" → Can't create pages
- "Remember this for later" → No persistent memory

---

## How LLM Sees Its Capabilities

The LLM receives this documentation every time you ask a question:

```
## AVAILABLE TOOLS

### search_notion
Search for pages/notes in Notion
Parameters: query (string, required)

### get_recent_notion_updates
Get recently updated Notion pages
Parameters: days (integer, optional, default: 7)

### get_notion_page_content
Get full content of a specific Notion page
Parameters: page_id (string, required)

[... calendar and email tools if configured ...]

## HOW TO USE TOOLS
[Detailed instructions with examples]

## CRITICAL - NEVER HALLUCINATE
⚠️ Only show data from actual tool results
⚠️ Don't make up tasks, events, or notes
⚠️ If result is empty, say so
```

---

## Extending The Agent

### Quick Wins (10-30 minutes)

1. **Expose `get_database_entries`** (line 53 in `notion.py`)
   - Already implemented, just not in ToolRegistry
   - Would enable structured database queries
   - Example: "Show all tasks with status 'In Progress'"

### Medium Effort (1-3 hours)

2. **Implement `create_notion_page`**
   - Notion API: `client.pages.create()`
   - Would enable: "Create a note about X"

3. **Implement `update_todo_status`**
   - Notion API: `client.blocks.update()`
   - Would enable: "Mark X as done"

4. **Implement `append_to_page`**
   - Notion API: `client.blocks.children.append()`
   - Would enable: "Add this to my notes"

### Big Effort (1-2 days)

5. **Add conversation persistence**
   - Save to SQLite database
   - Load previous conversations
   - Would enable: "What did we talk about yesterday?"

6. **Add proactive suggestions**
   - Analyze patterns in Notion
   - Suggest next actions
   - Would enable: Agent suggests "You should review X"

---

## Testing Your Agent

### Test Tool Calling
```bash
# Start server
./run.sh

# Open http://localhost:8000
# Try these queries:

1. "What's on my todo list?"
   Expected: Calls search_notion → get_notion_page_content

2. "Show me my recent notes"
   Expected: Calls get_recent_notion_updates

3. "Find notes about Python"
   Expected: Calls search_notion with query="Python"
```

### Test Anti-Hallucination
```bash
# Try trick questions:

1. "What's on my calendar?" (when calendar not configured)
   Expected: "❌ I cannot access calendar because..."

2. "Add X to my todo list"
   Expected: "❌ I cannot create/modify Notion pages..."

3. "What did we talk about yesterday?"
   Expected: "I don't have memory of previous conversations..."
```

### View Tool Execution
```bash
# Check action log in UI sidebar
# Or via API:
curl http://localhost:8000/api/actions

# Expected format:
{
  "actions": [
    {
      "timestamp": "2026-03-05T10:30:00",
      "action": "tool_decision",
      "status": "success",
      "details": "Decided to call: search_notion"
    },
    {
      "timestamp": "2026-03-05T10:30:01",
      "action": "tool_execution",
      "status": "success",
      "details": "Executed search_notion with query='todo'"
    }
  ]
}
```

---

## Troubleshooting

### Agent Is Hallucinating
1. Check temperature setting (should be 0.3 for Ollama)
2. Verify system prompt is being loaded
3. Try qwen2.5:14b instead of llama3.1:8b (larger model = less hallucination)

### Agent Not Calling Tools
1. Check tool registry initialization in logs
2. Verify integration is configured (check startup logs)
3. Check LLM response format (should be valid JSON)

### Tools Failing
1. Check action log for error messages
2. Verify API credentials (.env file)
3. Check network connectivity
4. Look at server logs for stack traces

---

## Key Files Reference

### Core Agentic System
- `src/core/assistant.py:80-150` - Main agentic loop
- `src/core/tools.py:89-162` - Tool documentation prompt
- `src/core/tools.py:165-334` - Tool registration
- `src/core/system_prompts.py` - Anti-hallucination rules

### Integrations
- `src/integrations/notion.py:24-51` - search_pages (exposed)
- `src/integrations/notion.py:53-83` - get_database_entries (NOT exposed)
- `src/integrations/notion.py:85-113` - get_page_content (exposed)
- `src/integrations/notion.py:223-289` - Recursive block extraction

### Configuration
- `.env` - LLM provider, API keys, integrations
- `src/core/config.py` - Settings validation

---

## Performance Metrics

### Current Baseline
- **Average response time**: 3-5 seconds (local Ollama)
- **Tool call latency**: 500ms-1s per Notion API call
- **Token usage**: ~1000-2000 tokens per conversation turn
- **Memory usage**: ~10GB (qwen2.5:14b loaded)

### Optimization Opportunities
1. Cache Notion search results (5 minute TTL)
2. Parallel tool execution for independent calls
3. Summarize old tool results to save tokens
4. Lazy load Ollama model (only when needed)

---

## Next Steps (Recommended Priority)

### Week 1: Expose Database Queries
- [ ] Add `get_database_entries` to ToolRegistry
- [ ] Test with structured Notion databases
- [ ] Document new capability

### Week 2: Add Write Operations
- [ ] Implement `create_notion_page()`
- [ ] Implement `append_to_page()`
- [ ] Implement `update_todo_status()`
- [ ] Add to ToolRegistry

### Week 3: Testing & Refinement
- [ ] Test all new tools thoroughly
- [ ] Gather usage data
- [ ] Improve error handling
- [ ] Add rate limiting

### Week 4: Deploy to Server
- [ ] Configure Linux server environment
- [ ] Set up systemd service
- [ ] Configure firewall
- [ ] Set up monitoring

---

## Success Metrics

### Current State
- ✅ Agent can read Notion data
- ✅ Agent chains tools intelligently
- ✅ Agent doesn't hallucinate (mostly)
- ✅ Action logging works
- ⚠️ Read-only (limits usefulness)

### Goal State
- ✅ Agent can read AND write Notion data
- ✅ Agent manages tasks autonomously
- ✅ Agent remembers context across sessions
- ✅ Agent suggests proactive actions
- ✅ Deployed on Linux server

**Current Usefulness**: 6/10 (good reader, can't act)
**Potential Usefulness**: 9/10 (with write operations)
