"""
FastAPI server for the personal assistant.
Provides REST API and web interface.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import os
import uuid

from ..core.config import get_settings
from ..core.assistant import PersonalAssistant
from ..core.context_builder import ContextBuilder
from ..integrations import GoogleCalendarIntegration, NotionIntegration, EmailIntegration
from ..llm import LLMFactory

# Initialize FastAPI app
app = FastAPI(
    title="Personal Assistant API",
    description="Intelligent personal assistant with calendar, notes, and email integration",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances (will be initialized on startup)
assistant: Optional[PersonalAssistant] = None
context_builder: Optional[ContextBuilder] = None
settings = get_settings()

# Session management - stores assistant instances per session
sessions = {}


# Request/Response models
class QuestionRequest(BaseModel):
    question: str
    include_context: bool = True


class BriefingResponse(BaseModel):
    date: str
    briefing: str


class PrioritiesResponse(BaseModel):
    priorities: str


class AnswerResponse(BaseModel):
    answer: str


@app.on_event("startup")
async def startup_event():
    """Initialize integrations on startup"""
    global assistant, context_builder

    try:
        # Initialize integrations
        calendar = None
        notion = None
        email = None

        print("🚀 Initializing Personal Assistant API...")

        # Initialize agentic logger
        from ..core.agentic_logger import init_agentic_logger
        logger = init_agentic_logger(
            enabled=settings.agentic_logging_enabled,
            verbose=settings.agentic_logging_verbose
        )

        if settings.agentic_logging_enabled:
            print(f"✅ Agentic logging enabled (verbose={settings.agentic_logging_verbose})")
        else:
            print("ℹ️  Agentic logging disabled")

        # Google Calendar
        if os.path.exists(settings.google_credentials_path):
            try:
                calendar = GoogleCalendarIntegration(
                    credentials_path=settings.google_credentials_path,
                    token_path=settings.google_token_path
                )
                # Authenticate in background to avoid blocking startup
                if calendar.authenticate():
                    print("✅ Google Calendar integration initialized")
                else:
                    print("⚠️  Google Calendar authentication failed")
                    calendar = None
            except Exception as e:
                print(f"⚠️  Google Calendar integration error: {e}")
                calendar = None
        else:
            print("ℹ️  Google Calendar not configured (credentials file not found)")

        # Notion
        if settings.notion_api_key:
            try:
                notion = NotionIntegration(
                    api_key=settings.notion_api_key,
                    database_id=settings.notion_database_id
                )
                print("✅ Notion integration initialized")
            except Exception as e:
                print(f"⚠️  Notion integration error: {e}")
                notion = None
        else:
            print("ℹ️  Notion not configured (API key not set)")

        # Email
        if settings.email_address and settings.email_password:
            try:
                email = EmailIntegration(
                    imap_server=settings.email_imap_server,
                    email_address=settings.email_address,
                    password=settings.email_password
                )
                print("✅ Email integration initialized")
            except Exception as e:
                print(f"⚠️  Email integration error: {e}")
                email = None
        else:
            print("ℹ️  Email not configured (credentials not set)")

        # Web Search
        web_search = None
        if settings.web_search_enabled:
            try:
                from ..integrations.web_search import WebSearchIntegration
                web_search = WebSearchIntegration(timeout=settings.web_search_timeout)
                print("✅ Web search integration initialized")
            except Exception as e:
                print(f"⚠️  Web search integration error: {e}")
                web_search = None
        else:
            print("ℹ️  Web search disabled (WEB_SEARCH_ENABLED=False)")

        # Initialize context builder
        context_builder = ContextBuilder(
            calendar=calendar,
            notion=notion,
            email=email,
            web_search=web_search
        )

        # Initialize LLM
        try:
            llm_config = settings.get_llm_config()
            llm = LLMFactory.create_llm(**llm_config)
            print(f"✅ LLM initialized ({settings.llm_provider})")

            # Initialize assistant
            assistant = PersonalAssistant(llm=llm, context_builder=context_builder)
            print("✅ Personal Assistant API initialized successfully!")

        except ValueError as e:
            print(f"❌ LLM Configuration Error: {e}")
            print("ℹ️  Please configure an LLM provider in your .env file")
            assistant = None
        except Exception as e:
            print(f"❌ LLM Initialization Error: {e}")
            assistant = None

    except Exception as e:
        print(f"❌ Error during startup: {e}")


@app.get("/chat", response_class=HTMLResponse)
async def chat_interface():
    """Serve chat interface"""
    import os
    from pathlib import Path

    # Get the project root directory
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent
    chat_file = project_root / "ui" / "chat.html"

    if not chat_file.exists():
        raise HTTPException(status_code=404, detail=f"Chat interface not found at {chat_file}")

    with open(chat_file, "r") as f:
        return HTMLResponse(content=f.read())


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve simple web interface"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Personal Assistant</title>
        <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
        <meta http-equiv="Pragma" content="no-cache">
        <meta http-equiv="Expires" content="0">
        <style>
            :root {
                --bg-primary: #0d1117;
                --bg-secondary: #161b22;
                --bg-tertiary: #21262d;
                --text-primary: #c9d1d9;
                --text-secondary: #8b949e;
                --accent-primary: #58a6ff;
                --accent-hover: #1f6feb;
                --border-color: #30363d;
                --success: #3fb950;
                --warning: #d29922;
                --error: #f85149;
            }

            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: var(--bg-primary);
                color: var(--text-primary);
                line-height: 1.6;
            }

            .container {
                background-color: var(--bg-secondary);
                border-radius: 12px;
                padding: 30px;
                box-shadow: 0 8px 24px rgba(0,0,0,0.4);
                border: 1px solid var(--border-color);
            }

            h1 {
                color: var(--text-primary);
                border-bottom: 2px solid var(--accent-primary);
                padding-bottom: 15px;
                margin-bottom: 20px;
                font-size: 2em;
            }

            h2 {
                color: var(--text-primary);
                margin-top: 30px;
                margin-bottom: 15px;
                font-size: 1.5em;
            }

            p {
                color: var(--text-secondary);
                margin-bottom: 20px;
            }

            .button {
                background-color: var(--accent-primary);
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 500;
                margin: 5px;
                transition: all 0.2s ease;
            }

            .button:hover {
                background-color: var(--accent-hover);
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(88, 166, 255, 0.3);
            }

            .button:active {
                transform: translateY(0);
            }

            .output {
                background-color: var(--bg-tertiary);
                border-left: 4px solid var(--accent-primary);
                padding: 20px;
                margin: 20px 0;
                border-radius: 6px;
                white-space: pre-wrap;
                font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, monospace;
                font-size: 14px;
                line-height: 1.6;
                color: var(--text-primary);
                min-height: 100px;
                max-height: 500px;
                overflow-y: auto;
            }

            .output::-webkit-scrollbar {
                width: 8px;
            }

            .output::-webkit-scrollbar-track {
                background: var(--bg-secondary);
                border-radius: 4px;
            }

            .output::-webkit-scrollbar-thumb {
                background: var(--border-color);
                border-radius: 4px;
            }

            .output::-webkit-scrollbar-thumb:hover {
                background: var(--text-secondary);
            }

            .endpoint {
                background-color: var(--bg-tertiary);
                padding: 12px;
                margin: 10px 0;
                border-radius: 6px;
                border: 1px solid var(--border-color);
                font-family: monospace;
                font-size: 13px;
            }

            .endpoint strong {
                color: var(--success);
                margin-right: 8px;
            }

            input[type="text"] {
                width: 100%;
                padding: 12px;
                margin: 10px 0;
                background-color: var(--bg-tertiary);
                border: 1px solid var(--border-color);
                border-radius: 6px;
                font-size: 14px;
                color: var(--text-primary);
                transition: border-color 0.2s ease;
            }

            input[type="text"]:focus {
                outline: none;
                border-color: var(--accent-primary);
                box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.1);
            }

            input[type="text"]::placeholder {
                color: var(--text-secondary);
            }

            .loading {
                color: var(--warning);
            }

            .error {
                color: var(--error);
                background-color: rgba(248, 81, 73, 0.1);
                border-left-color: var(--error);
            }

            .chat-container {
                display: flex;
                gap: 20px;
                margin: 20px 0;
            }

            .main-section {
                flex: 2;
            }

            .sidebar-section {
                flex: 1;
            }

            .chat-window {
                background-color: var(--bg-tertiary);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                height: 500px;
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }

            .chat-messages {
                flex: 1;
                overflow-y: auto;
                padding: 20px;
                display: flex;
                flex-direction: column;
                gap: 15px;
            }

            .chat-message {
                display: flex;
                gap: 12px;
                max-width: 85%;
                animation: fadeIn 0.3s ease;
            }

            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }

            .chat-message.user {
                align-self: flex-end;
                flex-direction: row-reverse;
            }

            .chat-message.assistant {
                align-self: flex-start;
            }

            .message-avatar {
                width: 32px;
                height: 32px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 16px;
                flex-shrink: 0;
            }

            .chat-message.user .message-avatar {
                background-color: var(--accent-primary);
            }

            .chat-message.assistant .message-avatar {
                background-color: var(--success);
            }

            .message-content {
                background-color: var(--bg-secondary);
                padding: 10px 14px;
                border-radius: 12px;
                border: 1px solid var(--border-color);
                white-space: pre-wrap;
                line-height: 1.5;
                font-size: 14px;
            }

            .chat-message.user .message-content {
                background-color: var(--accent-primary);
                color: white;
                border: none;
            }

            .chat-input-area {
                padding: 15px;
                background-color: var(--bg-secondary);
                border-top: 1px solid var(--border-color);
            }

            .chat-input-container {
                display: flex;
                gap: 10px;
                align-items: flex-end;
            }

            #chatInput {
                flex: 1;
                background-color: var(--bg-tertiary);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 10px 14px;
                color: var(--text-primary);
                font-size: 14px;
                font-family: inherit;
                resize: none;
                min-height: 42px;
                max-height: 150px;
            }

            #chatInput:focus {
                outline: none;
                border-color: var(--accent-primary);
                box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.1);
            }

            .action-log {
                background-color: var(--bg-tertiary);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 15px;
                max-height: 500px;
                overflow-y: auto;
            }

            .action-item {
                background-color: var(--bg-secondary);
                border: 1px solid var(--border-color);
                border-radius: 6px;
                padding: 10px;
                margin-bottom: 10px;
                font-size: 12px;
            }

            .action-item .timestamp {
                color: var(--text-secondary);
                font-size: 11px;
                margin-top: 5px;
            }

            .action-item .status {
                display: inline-block;
                margin-right: 5px;
            }

            .action-item.success .status { color: var(--success); }
            .action-item.error .status { color: var(--error); }
            .action-item.in_progress .status { color: var(--warning); }

            .loading-dots {
                display: flex;
                gap: 5px;
                padding: 10px;
            }

            .loading-dot {
                width: 8px;
                height: 8px;
                background-color: var(--text-secondary);
                border-radius: 50%;
                animation: pulse 1.4s ease-in-out infinite;
            }

            .loading-dot:nth-child(2) { animation-delay: 0.2s; }
            .loading-dot:nth-child(3) { animation-delay: 0.4s; }

            @keyframes pulse {
                0%, 80%, 100% { opacity: 0.4; }
                40% { opacity: 1; }
            }

            .empty-chat {
                text-align: center;
                padding: 40px 20px;
                color: var(--text-secondary);
            }

            .chat-messages::-webkit-scrollbar,
            .action-log::-webkit-scrollbar {
                width: 6px;
            }

            .chat-messages::-webkit-scrollbar-track,
            .action-log::-webkit-scrollbar-track {
                background: var(--bg-secondary);
            }

            .chat-messages::-webkit-scrollbar-thumb,
            .action-log::-webkit-scrollbar-thumb {
                background: var(--border-color);
                border-radius: 3px;
            }

            .button-group {
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
                margin-bottom: 10px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Personal Assistant</h1>
            <p>Welcome to your intelligent personal assistant!</p>

            <h2>Quick Actions</h2>
            <div class="button-group">
                <button class="button" onclick="getDailyBriefing()">📅 Daily Briefing</button>
                <button class="button" onclick="getEveningSummary()">🌙 Evening Summary</button>
                <button class="button" onclick="getPriorities()">⭐ Task Priorities</button>
                <button class="button" onclick="getNextAction()">➡️ Next Action</button>
                <button class="button" onclick="clearChat()" style="background-color: var(--error);">🗑️ Clear Chat</button>
            </div>

            <div class="chat-container">
                <div class="main-section">
                    <h2>💬 Chat</h2>
                    <div class="chat-window">
                        <div class="chat-messages" id="chatMessages">
                            <div class="empty-chat">
                                <h3>👋 Start chatting!</h3>
                                <p>Ask me anything about your schedule, notes, or emails</p>
                            </div>
                        </div>
                        <div class="chat-input-area">
                            <div class="chat-input-container">
                                <textarea
                                    id="chatInput"
                                    placeholder="Type your message..."
                                    rows="1"
                                    onkeydown="handleChatKeyPress(event)"
                                ></textarea>
                                <button class="button" onclick="sendChatMessage()">Send</button>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="sidebar-section">
                    <h2>📊 Action Log</h2>
                    <div class="action-log" id="actionLog">
                        <div class="empty-chat">
                            <p>No actions yet</p>
                        </div>
                    </div>
                </div>
            </div>

            <h2>API Endpoints</h2>
            <div class="endpoint"><strong>GET</strong> /api/briefing - Daily briefing</div>
            <div class="endpoint"><strong>GET</strong> /api/evening-summary - Evening summary</div>
            <div class="endpoint"><strong>GET</strong> /api/priorities - Task priorities</div>
            <div class="endpoint"><strong>GET</strong> /api/next-action - Suggested next action</div>
            <div class="endpoint"><strong>POST</strong> /api/ask - Ask a question</div>
            <div class="endpoint"><strong>GET</strong> /health - Health check</div>
        </div>

        <script>
            let isLoading = false;

            // Quick action handlers - these add to chat
            async function getDailyBriefing() {
                sendChatMessage('Give me my daily briefing');
            }

            async function getEveningSummary() {
                sendChatMessage('Give me my evening summary');
            }

            async function getPriorities() {
                sendChatMessage('What should I prioritize?');
            }

            async function getNextAction() {
                sendChatMessage('What should I do next?');
            }

            // Chat functions
            async function sendChatMessage(messageText) {
                const input = document.getElementById('chatInput');
                const message = messageText || input.value.trim();

                if (!message || isLoading) return;

                // Add user message
                addChatMessage('user', message);
                if (!messageText) {
                    input.value = '';
                    input.style.height = 'auto';
                }

                // Show loading
                isLoading = true;
                const loadingId = addLoadingMessage();
                startPolling(); // Start polling while waiting for response

                try {
                    const response = await fetch('/api/ask', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            question: message,
                            include_context: true
                        })
                    });

                    if (!response.ok) {
                        const error = await response.json();
                        throw new Error(error.detail || 'Failed to get response');
                    }

                    const data = await response.json();

                    // Remove loading and add response
                    removeMessage(loadingId);
                    addChatMessage('assistant', data.answer);

                    // Update action log
                    await updateActionLog();

                } catch (error) {
                    removeMessage(loadingId);
                    addChatMessage('assistant', `❌ Error: ${error.message}`);
                } finally {
                    isLoading = false;
                    stopPolling(); // Stop polling after response
                    await updateActionLog(); // One final update
                }
            }

            function addChatMessage(role, content) {
                const messages = document.getElementById('chatMessages');
                const emptyState = messages.querySelector('.empty-chat');
                if (emptyState) emptyState.remove();

                const messageDiv = document.createElement('div');
                messageDiv.className = `chat-message ${role}`;
                messageDiv.id = `msg-${Date.now()}`;

                const avatar = document.createElement('div');
                avatar.className = 'message-avatar';
                avatar.textContent = role === 'user' ? '👤' : '🤖';

                const contentDiv = document.createElement('div');
                contentDiv.className = 'message-content';
                contentDiv.textContent = content;

                messageDiv.appendChild(avatar);
                messageDiv.appendChild(contentDiv);
                messages.appendChild(messageDiv);

                messages.scrollTop = messages.scrollHeight;
                return messageDiv.id;
            }

            function addLoadingMessage() {
                const messages = document.getElementById('chatMessages');
                const loadingDiv = document.createElement('div');
                loadingDiv.className = 'chat-message assistant';
                const id = `loading-${Date.now()}`;
                loadingDiv.id = id;

                const avatar = document.createElement('div');
                avatar.className = 'message-avatar';
                avatar.textContent = '🤖';

                const loading = document.createElement('div');
                loading.className = 'message-content loading-dots';
                loading.innerHTML = '<div class="loading-dot"></div><div class="loading-dot"></div><div class="loading-dot"></div>';

                loadingDiv.appendChild(avatar);
                loadingDiv.appendChild(loading);
                messages.appendChild(loadingDiv);

                messages.scrollTop = messages.scrollHeight;
                return id;
            }

            function removeMessage(id) {
                const msg = document.getElementById(id);
                if (msg) msg.remove();
            }

            async function updateActionLog() {
                try {
                    const response = await fetch('/api/actions');
                    const data = await response.json();

                    const actionLog = document.getElementById('actionLog');
                    actionLog.innerHTML = '';

                    if (data.actions.length === 0) {
                        actionLog.innerHTML = '<div class="empty-chat"><p>No actions yet</p></div>';
                        return;
                    }

                    data.actions.reverse().forEach(action => {
                        const item = document.createElement('div');
                        item.className = `action-item ${action.status}`;

                        const statusIcon = action.status === 'success' ? '✅' :
                                         action.status === 'error' ? '❌' : '⏳';

                        item.innerHTML = `
                            <div class="status">${statusIcon}</div>
                            <strong>${action.action}</strong>
                            <div>${action.details}</div>
                            <div class="timestamp">${new Date(action.timestamp).toLocaleTimeString()}</div>
                        `;

                        actionLog.appendChild(item);
                    });
                } catch (error) {
                    console.error('Failed to update action log:', error);
                }
            }

            async function clearChat() {
                if (!confirm('Clear chat history?')) return;

                try {
                    await fetch('/api/session/reset', { method: 'POST' });
                    document.getElementById('chatMessages').innerHTML = `
                        <div class="empty-chat">
                            <h3>👋 Start chatting!</h3>
                            <p>Ask me anything about your schedule, notes, or emails</p>
                        </div>
                    `;
                    document.getElementById('actionLog').innerHTML = '<div class="empty-chat"><p>No actions yet</p></div>';
                } catch (error) {
                    alert('Failed to clear chat');
                }
            }

            function handleChatKeyPress(event) {
                if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault();
                    sendChatMessage();
                }
            }

            // Auto-resize textarea
            document.getElementById('chatInput').addEventListener('input', function() {
                this.style.height = 'auto';
                this.style.height = (this.scrollHeight) + 'px';
            });

            // Load action log on page load
            updateActionLog();

            // Smart polling - only poll during active requests
            let pollInterval = null;

            function startPolling() {
                if (!pollInterval) {
                    pollInterval = setInterval(updateActionLog, 2000);
                }
            }

            function stopPolling() {
                if (pollInterval) {
                    clearInterval(pollInterval);
                    pollInterval = null;
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "integrations": {
            "calendar": context_builder.calendar is not None if context_builder else False,
            "notion": context_builder.notion is not None if context_builder else False,
            "email": context_builder.email is not None if context_builder else False,
        }
    }


@app.get("/api/briefing", response_model=BriefingResponse)
async def get_daily_briefing():
    """Get daily briefing"""
    if not assistant:
        raise HTTPException(
            status_code=503,
            detail="❌ LLM is not configured.\n\nPlease configure an LLM provider in your .env file:\n\n"
                   "For Groq (free): Set GROQ_API_KEY\n"
                   "For Ollama (local): Install Ollama and set LLM_PROVIDER=ollama\n"
                   "For OpenAI: Set OPENAI_API_KEY\n"
                   "For Claude: Set ANTHROPIC_API_KEY\n\n"
                   "Then restart the server."
        )

    try:
        briefing = await assistant.generate_daily_briefing()
        return BriefingResponse(
            date=datetime.now().strftime("%Y-%m-%d"),
            briefing=briefing
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating briefing: {str(e)}")


@app.get("/api/evening-summary")
async def get_evening_summary():
    """Get evening summary"""
    if not assistant:
        raise HTTPException(
            status_code=503,
            detail="❌ LLM is not configured. Please configure an LLM provider in your .env file and restart the server."
        )

    try:
        summary = await assistant.generate_evening_summary()
        return {"summary": summary, "date": datetime.now().strftime("%Y-%m-%d")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")


@app.get("/api/priorities", response_model=PrioritiesResponse)
async def get_priorities():
    """Get task priorities"""
    if not assistant:
        raise HTTPException(
            status_code=503,
            detail="❌ LLM is not configured. Please configure an LLM provider in your .env file and restart the server."
        )

    try:
        priorities = await assistant.prioritize_tasks()
        return PrioritiesResponse(priorities=priorities)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting priorities: {str(e)}")


@app.get("/api/next-action")
async def get_next_action():
    """Get suggested next action"""
    if not assistant:
        raise HTTPException(
            status_code=503,
            detail="❌ LLM is not configured. Please configure an LLM provider in your .env file and restart the server."
        )

    try:
        suggestion = await assistant.suggest_next_action()
        return {"suggestion": suggestion, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting next action: {str(e)}")


@app.post("/api/ask", response_model=AnswerResponse)
async def ask_question(request: QuestionRequest):
    """Ask the assistant a question"""
    if not assistant:
        raise HTTPException(
            status_code=503,
            detail="❌ LLM is not configured.\n\nPlease configure an LLM provider in your .env file:\n\n"
                   "For Groq (free): Set GROQ_API_KEY\n"
                   "For Ollama (local): Install Ollama and set LLM_PROVIDER=ollama\n"
                   "For OpenAI: Set OPENAI_API_KEY\n"
                   "For Claude: Set ANTHROPIC_API_KEY\n\n"
                   "Then restart the server."
        )

    try:
        # Use agentic version that can call tools
        answer = await assistant.answer_question_agentic(
            question=request.question,
            include_context=request.include_context,
            max_iterations=10  # Increased for complex queries like tutorials, research
        )
        return AnswerResponse(answer=answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error answering question: {str(e)}")


@app.post("/api/session/reset")
async def reset_session():
    """Reset conversation history"""
    if not assistant:
        raise HTTPException(status_code=503, detail="Assistant not initialized")

    assistant.clear_conversation_history()
    return {"status": "success", "message": "Conversation history cleared"}


@app.get("/api/session/history")
async def get_conversation_history():
    """Get conversation history"""
    if not assistant:
        raise HTTPException(status_code=503, detail="Assistant not initialized")

    history = [
        {
            "role": msg.role,
            "content": msg.content,
        }
        for msg in assistant.conversation_history
        if msg.role != "system"  # Don't send system messages
    ]

    return {"history": history}


@app.get("/api/actions")
async def get_action_log():
    """Get recent action logs"""
    if not assistant:
        raise HTTPException(status_code=503, detail="Assistant not initialized")

    actions = assistant.get_recent_actions(limit=20)
    return {"actions": actions}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=True
    )
