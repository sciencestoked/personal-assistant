"""
FastAPI server for the personal assistant.
Provides REST API and web interface.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import os

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

# Global instances (will be initialized on startup)
assistant: Optional[PersonalAssistant] = None
context_builder: Optional[ContextBuilder] = None
settings = get_settings()


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

        # Initialize context builder
        context_builder = ContextBuilder(
            calendar=calendar,
            notion=notion,
            email=email
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


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve simple web interface"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Personal Assistant</title>
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
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Personal Assistant</h1>
            <p>Welcome to your intelligent personal assistant! Use the buttons below to interact.</p>

            <h2>Quick Actions</h2>
            <button class="button" onclick="getDailyBriefing()">📅 Daily Briefing</button>
            <button class="button" onclick="getEveningSummary()">🌙 Evening Summary</button>
            <button class="button" onclick="getPriorities()">⭐ Task Priorities</button>
            <button class="button" onclick="getNextAction()">➡️ Next Action</button>

            <h2>Ask a Question</h2>
            <input type="text" id="question" placeholder="Ask me anything about your schedule, notes, or emails...">
            <button class="button" onclick="askQuestion()">Ask</button>

            <h2>Response</h2>
            <div class="output" id="output">Results will appear here...</div>

            <h2>API Endpoints</h2>
            <div class="endpoint"><strong>GET</strong> /api/briefing - Daily briefing</div>
            <div class="endpoint"><strong>GET</strong> /api/evening-summary - Evening summary</div>
            <div class="endpoint"><strong>GET</strong> /api/priorities - Task priorities</div>
            <div class="endpoint"><strong>GET</strong> /api/next-action - Suggested next action</div>
            <div class="endpoint"><strong>POST</strong> /api/ask - Ask a question</div>
            <div class="endpoint"><strong>GET</strong> /health - Health check</div>
        </div>

        <script>
            async function handleRequest(fetchFn, loadingMsg = 'Loading...') {
                const output = document.getElementById('output');
                output.textContent = loadingMsg;
                output.classList.remove('error');

                try {
                    const result = await fetchFn();
                    output.textContent = result;
                } catch (error) {
                    output.classList.add('error');
                    output.textContent = `❌ Error: ${error.message}\n\nPlease check your configuration and make sure all required services are running.`;
                }
            }

            async function getDailyBriefing() {
                await handleRequest(async () => {
                    const response = await fetch('/api/briefing');
                    if (!response.ok) {
                        const error = await response.json();
                        throw new Error(error.detail || 'Failed to get daily briefing');
                    }
                    const data = await response.json();
                    return data.briefing;
                }, 'Generating your daily briefing...');
            }

            async function getEveningSummary() {
                await handleRequest(async () => {
                    const response = await fetch('/api/evening-summary');
                    if (!response.ok) {
                        const error = await response.json();
                        throw new Error(error.detail || 'Failed to get evening summary');
                    }
                    const data = await response.json();
                    return data.summary;
                }, 'Generating your evening summary...');
            }

            async function getPriorities() {
                await handleRequest(async () => {
                    const response = await fetch('/api/priorities');
                    if (!response.ok) {
                        const error = await response.json();
                        throw new Error(error.detail || 'Failed to get priorities');
                    }
                    const data = await response.json();
                    return data.priorities;
                }, 'Analyzing your priorities...');
            }

            async function getNextAction() {
                await handleRequest(async () => {
                    const response = await fetch('/api/next-action');
                    if (!response.ok) {
                        const error = await response.json();
                        throw new Error(error.detail || 'Failed to get next action');
                    }
                    const data = await response.json();
                    return data.suggestion;
                }, 'Finding your next best action...');
            }

            async function askQuestion() {
                const question = document.getElementById('question').value;
                if (!question) {
                    const output = document.getElementById('output');
                    output.classList.add('error');
                    output.textContent = '❌ Please enter a question';
                    return;
                }

                await handleRequest(async () => {
                    const response = await fetch('/api/ask', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ question: question, include_context: true })
                    });
                    if (!response.ok) {
                        const error = await response.json();
                        throw new Error(error.detail || 'Failed to get answer');
                    }
                    const data = await response.json();
                    return data.answer;
                }, 'Thinking...');
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
        answer = await assistant.answer_question(
            question=request.question,
            include_context=request.include_context
        )
        return AnswerResponse(answer=answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error answering question: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=True
    )
