"""
Agentic logger for tracking agent's reasoning and decision-making process.
Provides rich, colored console output showing what the agent is thinking.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
import json


class AgenticLogger:
    """Logger for agent's reasoning and actions"""

    def __init__(self, enabled: bool = True, verbose: bool = False):
        """
        Initialize agentic logger.

        Args:
            enabled: Whether logging is enabled
            verbose: Show detailed debug information
        """
        self.enabled = enabled
        self.verbose = verbose
        self.console = Console()
        self.current_iteration = 0

    def log_question(self, question: str) -> None:
        """Log user's question"""
        if not self.enabled:
            return

        self.console.print()
        self.console.print(Panel(
            f"[bold cyan]💭 User Question:[/bold cyan]\n{question}",
            border_style="cyan",
            box=box.ROUNDED
        ))

    def log_thinking(self, thought: str) -> None:
        """Log agent's thought process"""
        if not self.enabled:
            return

        self.console.print(
            f"\n[bold yellow]🧠 Agent Thinking:[/bold yellow] [dim]{thought}[/dim]"
        )

    def log_tool_decision(self, tool_name: str, parameters: Dict[str, Any],
                         reasoning: str, iteration: int) -> None:
        """Log agent's decision to use a tool"""
        if not self.enabled:
            return

        self.current_iteration = iteration

        # Create parameters table
        param_str = json.dumps(parameters, indent=2)

        self.console.print()
        self.console.print(Panel(
            f"[bold green]🔧 Tool Decision (Iteration {iteration}):[/bold green]\n\n"
            f"[bold]Tool:[/bold] [cyan]{tool_name}[/cyan]\n\n"
            f"[bold]Reasoning:[/bold]\n{reasoning}\n\n"
            f"[bold]Parameters:[/bold]\n[dim]{param_str}[/dim]",
            border_style="green",
            box=box.ROUNDED
        ))

    def log_tool_execution_start(self, tool_name: str) -> None:
        """Log tool execution start"""
        if not self.enabled:
            return

        self.console.print(
            f"[bold blue]⚙️  Executing:[/bold blue] [cyan]{tool_name}[/cyan]...",
            end=""
        )

    def log_tool_execution_end(self, tool_name: str, success: bool,
                               duration_ms: float, result_preview: str = None) -> None:
        """Log tool execution result"""
        if not self.enabled:
            return

        if success:
            status = "[bold green]✅ Success[/bold green]"
            icon = "✅"
        else:
            status = "[bold red]❌ Failed[/bold red]"
            icon = "❌"

        self.console.print(f" {icon} [dim]({duration_ms:.0f}ms)[/dim]")

        if result_preview and self.verbose:
            preview = result_preview[:200] + "..." if len(result_preview) > 200 else result_preview
            self.console.print(f"[dim]   Result preview: {preview}[/dim]")

    def log_tool_result(self, tool_name: str, success: bool, result: Any = None,
                       error: str = None) -> None:
        """Log detailed tool result"""
        if not self.enabled:
            return

        if success:
            # Format result for display
            if isinstance(result, list):
                result_str = f"[dim]Returned {len(result)} items[/dim]"
                if self.verbose and len(result) > 0:
                    result_str += f"\n[dim]{json.dumps(result[0], indent=2)}...[/dim]"
            elif isinstance(result, dict):
                result_str = f"[dim]Returned dict with {len(result)} keys[/dim]"
                if self.verbose:
                    result_str += f"\n[dim]{json.dumps(result, indent=2)[:500]}...[/dim]"
            else:
                result_str = f"[dim]{str(result)[:200]}...[/dim]" if result else "[dim]No content[/dim]"

            self.console.print(
                f"[bold green]📦 Tool Result:[/bold green] {result_str}"
            )
        else:
            self.console.print(
                f"[bold red]❌ Tool Error:[/bold red] [red]{error}[/red]"
            )

    def log_no_tool_needed(self, reasoning: str) -> None:
        """Log when agent decides no tool is needed"""
        if not self.enabled:
            return

        self.console.print()
        self.console.print(
            f"[bold magenta]🎯 Decision:[/bold magenta] [dim]No tool needed - responding directly[/dim]"
        )
        if reasoning and self.verbose:
            self.console.print(f"[dim]   Reasoning: {reasoning}[/dim]")

    def log_final_answer(self, answer: str, total_iterations: int,
                         total_time_ms: float) -> None:
        """Log final answer to user"""
        if not self.enabled:
            return

        answer_preview = answer[:150] + "..." if len(answer) > 150 else answer

        self.console.print()
        self.console.print(Panel(
            f"[bold green]💬 Final Answer:[/bold green]\n\n"
            f"{answer_preview}\n\n"
            f"[dim]Iterations: {total_iterations} | Time: {total_time_ms:.0f}ms[/dim]",
            border_style="green",
            box=box.ROUNDED
        ))

    def log_error(self, error: str, context: str = None) -> None:
        """Log an error"""
        if not self.enabled:
            return

        error_text = f"[bold red]❌ Error:[/bold red] {error}"
        if context:
            error_text += f"\n[dim]Context: {context}[/dim]"

        self.console.print()
        self.console.print(Panel(
            error_text,
            border_style="red",
            box=box.ROUNDED
        ))

    def log_available_tools(self, tools: list[str]) -> None:
        """Log available tools at startup"""
        if not self.enabled or not self.verbose:
            return

        table = Table(title="Available Tools", box=box.ROUNDED)
        table.add_column("Tool Name", style="cyan")
        table.add_column("Integration", style="yellow")

        for tool in tools:
            # Extract integration from tool name prefix
            if "notion" in tool:
                integration = "Notion"
            elif "calendar" in tool:
                integration = "Calendar"
            elif "email" in tool:
                integration = "Email"
            elif "web" in tool or "weather" in tool or "news" in tool or "search" in tool:
                integration = "Web Search"
            else:
                integration = "General"

            table.add_row(tool, integration)

        self.console.print()
        self.console.print(table)

    def log_integration_status(self, integrations: Dict[str, bool]) -> None:
        """Log integration status at startup"""
        if not self.enabled:
            return

        status_lines = []
        for name, enabled in integrations.items():
            icon = "✅" if enabled else "❌"
            status = "[green]Enabled[/green]" if enabled else "[red]Disabled[/red]"
            status_lines.append(f"{icon} {name.title()}: {status}")

        self.console.print()
        self.console.print(Panel(
            "\n".join(status_lines),
            title="[bold]Integration Status[/bold]",
            border_style="blue",
            box=box.ROUNDED
        ))

    def log_session_start(self) -> None:
        """Log session start"""
        if not self.enabled:
            return

        self.console.print()
        self.console.print(Panel(
            "[bold green]🚀 Agentic Session Started[/bold green]\n\n"
            "[dim]Agentic logging enabled - you'll see the agent's reasoning process[/dim]",
            border_style="green",
            box=box.ROUNDED
        ))

    def log_llm_response_raw(self, response: str) -> None:
        """Log raw LLM response (verbose only)"""
        if not self.enabled or not self.verbose:
            return

        preview = response[:300] + "..." if len(response) > 300 else response
        self.console.print(f"\n[dim]📝 Raw LLM Response:[/dim]\n[dim]{preview}[/dim]")

    def disable(self) -> None:
        """Disable logging"""
        self.enabled = False

    def enable(self) -> None:
        """Enable logging"""
        self.enabled = True

    def set_verbose(self, verbose: bool) -> None:
        """Set verbose mode"""
        self.verbose = verbose


# Global logger instance
_global_logger: Optional[AgenticLogger] = None


def get_agentic_logger() -> AgenticLogger:
    """Get global agentic logger instance"""
    global _global_logger
    if _global_logger is None:
        _global_logger = AgenticLogger(enabled=True, verbose=False)
    return _global_logger


def init_agentic_logger(enabled: bool = True, verbose: bool = False) -> AgenticLogger:
    """Initialize global agentic logger"""
    global _global_logger
    _global_logger = AgenticLogger(enabled=enabled, verbose=verbose)
    return _global_logger
