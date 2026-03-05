"""
Main assistant logic combining LLM and context for intelligent decisions.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import re
from ..llm import LLMFactory, BaseLLM, Message
from .context_builder import ContextBuilder
from .config import get_settings
from .system_prompts import get_base_system_prompt, get_chat_system_prompt, get_action_log_entry
from .tools import ToolRegistry, create_tool_registry


class IntegrationNotConfiguredError(Exception):
    """Raised when an integration is not configured"""
    pass


class PersonalAssistant:
    """Main personal assistant class"""

    def __init__(self, llm: BaseLLM, context_builder: ContextBuilder):
        """
        Initialize the personal assistant.

        Args:
            llm: LLM provider instance
            context_builder: Context builder instance
        """
        self.llm = llm
        self.context = context_builder
        self.settings = get_settings()
        self.conversation_history: List[Message] = []
        self.action_log: List[Dict[str, Any]] = []

        # Get available integrations for system prompt
        self.available_integrations = {
            'calendar': context_builder.calendar is not None,
            'notion': context_builder.notion is not None,
            'email': context_builder.email is not None
        }

        # Initialize tool registry
        self.tools = create_tool_registry(context_builder)

    def log_action(self, action: str, status: str, details: str = "") -> None:
        """Log an action for visibility"""
        log_entry = get_action_log_entry(action, status, details)
        self.action_log.append(log_entry)
        # Keep only last 50 actions
        if len(self.action_log) > 50:
            self.action_log = self.action_log[-50:]

    def get_recent_actions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent action logs"""
        return self.action_log[-limit:]

    def clear_conversation_history(self) -> None:
        """Clear conversation history (called on session reset)"""
        self.conversation_history = []
        self.action_log = []

    def _extract_tool_call(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract tool call from LLM response"""
        # Look for JSON code block
        json_pattern = r'```json\s*(\{.*?\})\s*```'
        match = re.search(json_pattern, response, re.DOTALL)

        if match:
            try:
                tool_call = json.loads(match.group(1))
                if "tool" in tool_call and "parameters" in tool_call:
                    return tool_call
            except json.JSONDecodeError:
                pass

        # Try to find JSON without code block
        try:
            # Find JSON object in response
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                potential_json = response[start:end]
                tool_call = json.loads(potential_json)
                if "tool" in tool_call and "parameters" in tool_call:
                    return tool_call
        except (json.JSONDecodeError, ValueError):
            pass

        return None

    async def _execute_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call and return the result"""
        tool_name = tool_call.get("tool")
        parameters = tool_call.get("parameters", {})
        thought = tool_call.get("thought", "")

        self.log_action(f"tool_call:{tool_name}", "in_progress", thought)

        # Get the tool
        tool = self.tools.get_tool(tool_name)

        if not tool:
            self.log_action(f"tool_call:{tool_name}", "error", f"Tool '{tool_name}' not found")
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found. Available tools: {list(self.tools.tools.keys())}"
            }

        # Execute the tool
        result = await tool.execute(**parameters)

        if result["success"]:
            self.log_action(f"tool_call:{tool_name}", "success", f"Tool executed successfully")
        else:
            self.log_action(f"tool_call:{tool_name}", "error", f"Tool failed: {result['error']}")

        return result

    async def generate_daily_briefing(self, target_date: Optional[datetime] = None) -> str:
        """
        Generate a daily briefing for the user.

        Args:
            target_date: Date to generate briefing for (defaults to today)

        Returns:
            Daily briefing text
        """
        if target_date is None:
            target_date = datetime.now()

        # Check what integrations are available
        missing_integrations = []
        if not self.context.calendar:
            missing_integrations.append("Google Calendar")
        if not self.context.notion:
            missing_integrations.append("Notion")
        if not self.context.email:
            missing_integrations.append("Email")

        # Build context for the day
        context = await self.context.build_daily_context(target_date)
        context_summary = self.context.build_context_summary(context)

        # Add integration status to context
        if missing_integrations:
            context_summary += f"\n\n⚠️ Note: The following integrations are not configured: {', '.join(missing_integrations)}"
            context_summary += "\nConfigure them in your .env file for full functionality."

        # Create prompt for LLM
        system_prompt = """You are a helpful personal assistant. Your job is to create a concise,
actionable daily briefing for the user. Focus on:
1. Key calendar events and meetings
2. Important unread emails that need attention
3. Recent notes or tasks that might be relevant
4. Any potential conflicts or important deadlines

Keep the briefing concise but informative. Use a friendly, professional tone."""

        user_prompt = f"""Please create a daily briefing for {target_date.strftime('%A, %B %d, %Y')}.

Here's the context:

{context_summary}

Provide a clear, structured briefing that helps me prioritize my day."""

        messages = [
            self.llm.create_system_message(system_prompt),
            self.llm.create_user_message(user_prompt)
        ]

        # Generate briefing
        briefing = await self.llm.generate(messages, temperature=0.7)
        return briefing

    async def generate_evening_summary(self) -> str:
        """
        Generate an evening summary of the day.

        Returns:
            Evening summary text
        """
        today = datetime.now()
        context = await self.context.build_daily_context(today)
        context_summary = self.context.build_context_summary(context)

        system_prompt = """You are a helpful personal assistant. Create a brief evening summary
that helps the user reflect on their day and prepare for tomorrow. Focus on:
1. What was scheduled today
2. Any important emails received
3. Gentle reminders for tomorrow if there are important events
4. A positive, encouraging tone

Keep it brief and helpful."""

        user_prompt = f"""Please create an evening summary for today ({today.strftime('%A, %B %d, %Y')}).

Today's context:

{context_summary}

Help me wind down and prepare for tomorrow."""

        messages = [
            self.llm.create_system_message(system_prompt),
            self.llm.create_user_message(user_prompt)
        ]

        summary = await self.llm.generate(messages, temperature=0.7)
        return summary

    async def prioritize_tasks(self) -> str:
        """
        Analyze context and suggest task priorities.

        Returns:
            Task prioritization recommendations
        """
        context = await self.context.build_weekly_context()
        context_summary = self.context.build_context_summary(context)

        system_prompt = """You are a helpful personal assistant specializing in task prioritization.
Analyze the user's calendar, emails, and notes to suggest what they should focus on.

Consider:
1. Urgency (deadlines, time-sensitive matters)
2. Importance (impact, consequences)
3. Dependencies (what needs to happen first)
4. Balance (don't overload any single day)

Provide clear, actionable recommendations."""

        user_prompt = f"""Based on my current context, what should I prioritize?

{context_summary}

Please suggest:
1. Top 3 priorities for today
2. Important tasks for this week
3. Any potential issues or conflicts to address"""

        messages = [
            self.llm.create_system_message(system_prompt),
            self.llm.create_user_message(user_prompt)
        ]

        recommendations = await self.llm.generate(messages, temperature=0.7)
        return recommendations

    async def process_email_batch(self, emails: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process a batch of emails and extract actionable items.

        Args:
            emails: List of email dictionaries

        Returns:
            Dictionary with categorized emails and extracted tasks
        """
        # Create email summary for LLM
        email_summaries = []
        for i, email in enumerate(emails[:20], 1):  # Limit to 20
            summary = f"{i}. From: {email.get('from', 'Unknown')}\n"
            summary += f"   Subject: {email.get('subject', 'No subject')}\n"
            body_preview = email.get('body', '')[:200]
            summary += f"   Preview: {body_preview}...\n"
            email_summaries.append(summary)

        email_context = "\n".join(email_summaries)

        system_prompt = """You are a helpful personal assistant that processes emails.
Analyze the emails and:
1. Categorize them (urgent, important, informational, spam/low-priority)
2. Extract any action items or tasks
3. Identify emails that need immediate attention
4. Suggest draft responses where appropriate

Be concise and actionable."""

        user_prompt = f"""Please process these emails:

{email_context}

Provide:
1. Emails requiring immediate attention
2. Extracted action items/tasks
3. Suggested categorization"""

        messages = [
            self.llm.create_system_message(system_prompt),
            self.llm.create_user_message(user_prompt)
        ]

        analysis = await self.llm.generate(messages, temperature=0.5)

        return {
            "analysis": analysis,
            "processed_count": len(emails)
        }

    async def answer_question_agentic(self, question: str, include_context: bool = True, max_iterations: int = 5) -> str:
        """
        Answer a user question with agentic tool use.
        Can call tools multiple times to accomplish the task.

        Args:
            question: User's question
            include_context: Whether to include calendar/notes/email context
            max_iterations: Maximum number of tool calls allowed

        Returns:
            Final answer to the question
        """
        # Check for integration-specific questions first
        question_lower = question.lower()

        if "notion" in question_lower and not self.context.notion:
            return "❌ Notion integration is not configured.\n\nTo access your Notion notes:\n1. Get a Notion API key from https://www.notion.so/my-integrations\n2. Add NOTION_API_KEY to your .env file\n3. Add your NOTION_DATABASE_ID to your .env file\n4. Restart the assistant"

        if ("calendar" in question_lower or "meeting" in question_lower or "event" in question_lower) and not self.context.calendar:
            return "❌ Google Calendar integration is not configured.\n\nTo access your calendar:\n1. Get Google Calendar API credentials from https://console.cloud.google.com/\n2. Download credentials and save as config/google_credentials.json\n3. Update GOOGLE_CREDENTIALS_PATH in your .env file\n4. Restart the assistant"

        if ("email" in question_lower or "mail" in question_lower) and not self.context.email:
            return "❌ Email integration is not configured.\n\nTo access your emails:\n1. Set EMAIL_ADDRESS in your .env file\n2. Set EMAIL_PASSWORD (use app password for Gmail) in your .env file\n3. Set EMAIL_IMAP_SERVER (e.g., imap.gmail.com) in your .env file\n4. Restart the assistant"

        messages = []

        # System message with strict boundaries AND tools
        system_prompt = get_chat_system_prompt(self.available_integrations)
        system_prompt += "\n\n" + self.tools.tools_to_prompt(self.available_integrations)
        messages.append(self.llm.create_system_message(system_prompt))

        # Log the action
        self.log_action("answer_question_agentic", "in_progress", f"Question: {question[:100]}")

        # Add context if requested
        if include_context:
            missing_integrations = []
            if not self.context.calendar:
                missing_integrations.append("Google Calendar")
            if not self.context.notion:
                missing_integrations.append("Notion")
            if not self.context.email:
                missing_integrations.append("Email")

            context = await self.context.build_daily_context()
            context_summary = self.context.build_context_summary(context)

            if missing_integrations:
                context_summary += f"\n\n⚠️ Missing integrations: {', '.join(missing_integrations)}"

            context_message = f"Current context:\n\n{context_summary}"
            messages.append(self.llm.create_user_message(context_message))

        # Add conversation history
        messages.extend(self.conversation_history[-6:])

        # Add current question
        messages.append(self.llm.create_user_message(question))

        # Agentic loop - allow multiple tool calls
        iteration = 0
        while iteration < max_iterations:
            iteration += 1

            try:
                # Generate response
                response = await self.llm.generate(messages, temperature=0.7)

                # Check if response contains a tool call
                tool_call = self._extract_tool_call(response)

                if tool_call:
                    # Log the tool call
                    self.log_action(
                        "tool_decision",
                        "success",
                        f"Decided to call: {tool_call.get('tool')} - {tool_call.get('thought', '')}"
                    )

                    # Execute the tool
                    tool_result = await self._execute_tool_call(tool_call)

                    # Add tool result to conversation
                    if tool_result["success"]:
                        result_message = f"✅ Tool '{tool_call['tool']}' executed successfully.\n\nResult:\n{json.dumps(tool_result['result'], indent=2)}\n\nYou can now use this information to answer the user's question."
                    else:
                        result_message = f"❌ Tool '{tool_call['tool']}' failed.\n\nError: {tool_result['error']}\n\nPlease explain this error to the user and suggest what they should do."

                    messages.append(self.llm.create_assistant_message(response))
                    messages.append(self.llm.create_user_message(result_message))

                    # Continue loop to let LLM process the result
                    continue
                else:
                    # No tool call, this is the final answer
                    self.log_action("answer_question_agentic", "success", "Final response generated")

                    # Update conversation history
                    self.conversation_history.append(self.llm.create_user_message(question))
                    self.conversation_history.append(self.llm.create_assistant_message(response))

                    return response

            except Exception as e:
                self.log_action("answer_question_agentic", "error", str(e))
                raise

        # Max iterations reached
        self.log_action("answer_question_agentic", "error", "Max iterations reached")
        return "I've reached the maximum number of tool calls. Please try breaking your request into smaller steps."

    async def answer_question(self, question: str, include_context: bool = True) -> str:
        """
        Answer a user question using available context.

        Args:
            question: User's question
            include_context: Whether to include calendar/notes/email context

        Returns:
            Answer to the question
        """
        # Check for integration-specific questions
        question_lower = question.lower()

        if "notion" in question_lower and not self.context.notion:
            return "❌ Notion integration is not configured.\n\nTo access your Notion notes:\n1. Get a Notion API key from https://www.notion.so/my-integrations\n2. Add NOTION_API_KEY to your .env file\n3. Add your NOTION_DATABASE_ID to your .env file\n4. Restart the assistant"

        if ("calendar" in question_lower or "meeting" in question_lower or "event" in question_lower) and not self.context.calendar:
            return "❌ Google Calendar integration is not configured.\n\nTo access your calendar:\n1. Get Google Calendar API credentials from https://console.cloud.google.com/\n2. Download credentials and save as config/google_credentials.json\n3. Update GOOGLE_CREDENTIALS_PATH in your .env file\n4. Restart the assistant"

        if ("email" in question_lower or "mail" in question_lower) and not self.context.email:
            return "❌ Email integration is not configured.\n\nTo access your emails:\n1. Set EMAIL_ADDRESS in your .env file\n2. Set EMAIL_PASSWORD (use app password for Gmail) in your .env file\n3. Set EMAIL_IMAP_SERVER (e.g., imap.gmail.com) in your .env file\n4. Restart the assistant"

        messages = []

        # System message with strict boundaries
        system_prompt = get_chat_system_prompt(self.available_integrations)
        messages.append(self.llm.create_system_message(system_prompt))

        # Log the action
        self.log_action("answer_question", "in_progress", f"Question: {question[:100]}")

        # Add context if requested
        if include_context:
            # Check what integrations are available
            missing_integrations = []
            if not self.context.calendar:
                missing_integrations.append("Google Calendar")
            if not self.context.notion:
                missing_integrations.append("Notion")
            if not self.context.email:
                missing_integrations.append("Email")

            context = await self.context.build_daily_context()
            context_summary = self.context.build_context_summary(context)

            if missing_integrations:
                context_summary += f"\n\n⚠️ Missing integrations: {', '.join(missing_integrations)}"

            context_message = f"Current context:\n\n{context_summary}"
            messages.append(self.llm.create_user_message(context_message))

        # Add conversation history
        messages.extend(self.conversation_history[-6:])  # Last 3 exchanges

        # Add current question
        messages.append(self.llm.create_user_message(question))

        # Generate response
        try:
            response = await self.llm.generate(messages, temperature=0.7)
            self.log_action("answer_question", "success", "Response generated")

            # Update conversation history
            self.conversation_history.append(self.llm.create_user_message(question))
            self.conversation_history.append(self.llm.create_assistant_message(response))

            return response
        except Exception as e:
            self.log_action("answer_question", "error", str(e))
            raise

    async def suggest_next_action(self) -> str:
        """
        Suggest what the user should do next based on current context.

        Returns:
            Suggestion for next action
        """
        context = await self.context.build_daily_context()
        context_summary = self.context.build_context_summary(context)

        now = datetime.now()
        current_time = now.strftime("%H:%M")
        current_day = now.strftime("%A")

        system_prompt = """You are a helpful personal assistant. Based on the current time
and the user's schedule, suggest the most appropriate next action. Be specific and
actionable. Consider:
1. Upcoming meetings or events
2. Urgent emails
3. Time of day and energy levels
4. Context and priorities"""

        user_prompt = f"""It's {current_time} on {current_day}. What should I do next?

Current context:

{context_summary}

Suggest one specific action I should take right now."""

        messages = [
            self.llm.create_system_message(system_prompt),
            self.llm.create_user_message(user_prompt)
        ]

        suggestion = await self.llm.generate(messages, temperature=0.7)
        return suggestion
