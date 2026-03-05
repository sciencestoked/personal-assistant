#!/usr/bin/env python3
"""
CLI interface for the personal assistant.
Provides quick access to assistant features from the command line.
"""

import typer
import asyncio
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from datetime import datetime
from typing import Optional

from .core.config import get_settings
from .core.assistant import PersonalAssistant
from .core.context_builder import ContextBuilder
from .integrations import GoogleCalendarIntegration, NotionIntegration, EmailIntegration
from .llm import LLMFactory

app = typer.Typer(help="Personal Assistant CLI")
console = Console()
settings = get_settings()


def get_assistant() -> PersonalAssistant:
    """Initialize and return assistant instance"""
    # Initialize integrations
    calendar = None
    notion = None
    email = None

    # Google Calendar
    try:
        calendar = GoogleCalendarIntegration(
            credentials_path=settings.google_credentials_path,
            token_path=settings.google_token_path
        )
        if not calendar.authenticate():
            console.print("[yellow]Warning: Could not authenticate with Google Calendar[/yellow]")
            calendar = None
    except Exception as e:
        console.print(f"[yellow]Warning: Calendar integration not available: {e}[/yellow]")

    # Notion
    try:
        if settings.notion_api_key:
            notion = NotionIntegration(
                api_key=settings.notion_api_key,
                database_id=settings.notion_database_id
            )
    except Exception as e:
        console.print(f"[yellow]Warning: Notion integration not available: {e}[/yellow]")

    # Email
    try:
        if settings.email_address and settings.email_password:
            email = EmailIntegration(
                imap_server=settings.email_imap_server,
                email_address=settings.email_address,
                password=settings.email_password
            )
    except Exception as e:
        console.print(f"[yellow]Warning: Email integration not available: {e}[/yellow]")

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
    return PersonalAssistant(llm=llm, context_builder=context_builder)


@app.command()
def briefing():
    """Get your daily briefing"""
    console.print("\n[bold cyan]Generating your daily briefing...[/bold cyan]\n")

    async def run():
        assistant = get_assistant()
        result = await assistant.generate_daily_briefing()
        return result

    briefing_text = asyncio.run(run())

    md = Markdown(briefing_text)
    console.print(Panel(md, title=f"📅 Daily Briefing - {datetime.now().strftime('%A, %B %d, %Y')}",
                       border_style="cyan"))


@app.command()
def summary():
    """Get your evening summary"""
    console.print("\n[bold magenta]Generating your evening summary...[/bold magenta]\n")

    async def run():
        assistant = get_assistant()
        result = await assistant.generate_evening_summary()
        return result

    summary_text = asyncio.run(run())

    md = Markdown(summary_text)
    console.print(Panel(md, title="🌙 Evening Summary", border_style="magenta"))


@app.command()
def priorities():
    """Get task prioritization recommendations"""
    console.print("\n[bold green]Analyzing your priorities...[/bold green]\n")

    async def run():
        assistant = get_assistant()
        result = await assistant.prioritize_tasks()
        return result

    priorities_text = asyncio.run(run())

    md = Markdown(priorities_text)
    console.print(Panel(md, title="⭐ Task Priorities", border_style="green"))


@app.command()
def next():
    """Get suggestion for next action"""
    console.print("\n[bold yellow]Finding your next best action...[/bold yellow]\n")

    async def run():
        assistant = get_assistant()
        result = await assistant.suggest_next_action()
        return result

    suggestion = asyncio.run(run())

    md = Markdown(suggestion)
    console.print(Panel(md, title="➡️ Next Action", border_style="yellow"))


@app.command()
def ask(
    question: str = typer.Argument(..., help="Question to ask the assistant"),
    no_context: bool = typer.Option(False, "--no-context", help="Don't include calendar/email/notes context")
):
    """Ask the assistant a question"""
    console.print(f"\n[bold blue]Question:[/bold blue] {question}\n")
    console.print("[dim]Thinking...[/dim]\n")

    async def run():
        assistant = get_assistant()
        result = await assistant.answer_question(question, include_context=not no_context)
        return result

    answer = asyncio.run(run())

    md = Markdown(answer)
    console.print(Panel(md, title="💬 Answer", border_style="blue"))


@app.command()
def server(
    host: str = typer.Option("0.0.0.0", help="Server host"),
    port: int = typer.Option(8000, help="Server port"),
    reload: bool = typer.Option(False, help="Enable auto-reload"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Disable HTTP access logs (show only agentic logs)")
):
    """Start the web server"""
    import uvicorn
    console.print(f"\n[bold green]Starting server on {host}:{port}...[/bold green]\n")
    console.print(f"[dim]Open http://localhost:{port} in your browser[/dim]\n")

    # Configure log level based on quiet flag
    log_level = "error" if quiet else "info"
    access_log = not quiet

    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
        access_log=access_log
    )


@app.command()
def config():
    """Show current configuration"""
    console.print("\n[bold cyan]Current Configuration[/bold cyan]\n")

    config_info = f"""
**LLM Provider:** {settings.llm_provider}
**LLM Model:** {settings.llm_model}
**Database:** {settings.database_url}
**Server:** {settings.server_host}:{settings.server_port}

**Integrations:**
- Google Calendar: {"✓" if settings.google_credentials_path else "✗"}
- Notion: {"✓" if settings.notion_api_key else "✗"}
- Email: {"✓" if settings.email_address else "✗"}

**Scheduled Tasks:**
- Daily Briefing: {settings.daily_briefing_time}
- Evening Summary: {settings.evening_summary_time}
"""

    md = Markdown(config_info)
    console.print(Panel(md, title="⚙️ Configuration", border_style="cyan"))


@app.command()
def version():
    """Show version information"""
    console.print("\n[bold]Personal Assistant v1.0.0[/bold]")
    console.print("Intelligent assistant with calendar, notes, and email integration\n")


if __name__ == "__main__":
    app()
