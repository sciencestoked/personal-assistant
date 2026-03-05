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

        # Google Calendar
        if os.path.exists(settings.google_credentials_path):
            calendar = GoogleCalendarIntegration(
                credentials_path=settings.google_credentials_path,
                token_path=settings.google_token_path
            )
            # Authenticate in background to avoid blocking startup
            calendar.authenticate()

        # Notion
        if settings.notion_api_key:
            notion = NotionIntegration(
                api_key=settings.notion_api_key,
                database_id=settings.notion_database_id
            )

        # Email
        if settings.email_address and settings.email_password:
            email = EmailIntegration(
                imap_server=settings.email_imap_server,
                email_address=settings.email_address,
                password=settings.email_password
            )

        # Initialize context builder
        context_builder = ContextBuilder(
            calendar=calendar,
            notion=notion,
            email=email
        )

        # Initialize LLM
        llm_config = settings.get_llm_config()
        llm = LLMFactory.create_llm(**llm_config)

        # Initialize assistant
        assistant = PersonalAssistant(llm=llm, context_builder=context_builder)

        print("Personal Assistant API initialized successfully!")

    except Exception as e:
        print(f"Error during startup: {e}")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve simple web interface"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Personal Assistant</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                background-color: white;
                border-radius: 10px;
                padding: 30px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                border-bottom: 3px solid #4CAF50;
                padding-bottom: 10px;
            }
            .button {
                background-color: #4CAF50;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
                margin: 5px;
            }
            .button:hover {
                background-color: #45a049;
            }
            .output {
                background-color: #f9f9f9;
                border-left: 4px solid #4CAF50;
                padding: 15px;
                margin: 20px 0;
                border-radius: 5px;
                white-space: pre-wrap;
                font-family: monospace;
            }
            .endpoint {
                background-color: #e8f5e9;
                padding: 10px;
                margin: 10px 0;
                border-radius: 5px;
            }
            input[type="text"] {
                width: 100%;
                padding: 10px;
                margin: 10px 0;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 16px;
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
            async function getDailyBriefing() {
                document.getElementById('output').textContent = 'Loading...';
                const response = await fetch('/api/briefing');
                const data = await response.json();
                document.getElementById('output').textContent = data.briefing;
            }

            async function getEveningSummary() {
                document.getElementById('output').textContent = 'Loading...';
                const response = await fetch('/api/evening-summary');
                const data = await response.json();
                document.getElementById('output').textContent = data.summary;
            }

            async function getPriorities() {
                document.getElementById('output').textContent = 'Loading...';
                const response = await fetch('/api/priorities');
                const data = await response.json();
                document.getElementById('output').textContent = data.priorities;
            }

            async function getNextAction() {
                document.getElementById('output').textContent = 'Loading...';
                const response = await fetch('/api/next-action');
                const data = await response.json();
                document.getElementById('output').textContent = data.suggestion;
            }

            async function askQuestion() {
                const question = document.getElementById('question').value;
                if (!question) {
                    alert('Please enter a question');
                    return;
                }

                document.getElementById('output').textContent = 'Thinking...';
                const response = await fetch('/api/ask', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ question: question, include_context: true })
                });
                const data = await response.json();
                document.getElementById('output').textContent = data.answer;
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
        raise HTTPException(status_code=503, detail="Assistant not initialized")

    try:
        briefing = await assistant.generate_daily_briefing()
        return BriefingResponse(
            date=datetime.now().strftime("%Y-%m-%d"),
            briefing=briefing
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/evening-summary")
async def get_evening_summary():
    """Get evening summary"""
    if not assistant:
        raise HTTPException(status_code=503, detail="Assistant not initialized")

    try:
        summary = await assistant.generate_evening_summary()
        return {"summary": summary, "date": datetime.now().strftime("%Y-%m-%d")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/priorities", response_model=PrioritiesResponse)
async def get_priorities():
    """Get task priorities"""
    if not assistant:
        raise HTTPException(status_code=503, detail="Assistant not initialized")

    try:
        priorities = await assistant.prioritize_tasks()
        return PrioritiesResponse(priorities=priorities)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/next-action")
async def get_next_action():
    """Get suggested next action"""
    if not assistant:
        raise HTTPException(status_code=503, detail="Assistant not initialized")

    try:
        suggestion = await assistant.suggest_next_action()
        return {"suggestion": suggestion, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ask", response_model=AnswerResponse)
async def ask_question(request: QuestionRequest):
    """Ask the assistant a question"""
    if not assistant:
        raise HTTPException(status_code=503, detail="Assistant not initialized")

    try:
        answer = await assistant.answer_question(
            question=request.question,
            include_context=request.include_context
        )
        return AnswerResponse(answer=answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=True
    )
