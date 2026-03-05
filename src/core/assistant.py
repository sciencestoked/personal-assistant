"""
Main assistant logic combining LLM and context for intelligent decisions.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from ..llm import LLMFactory, BaseLLM, Message
from .context_builder import ContextBuilder
from .config import get_settings


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

        # Build context for the day
        context = await self.context.build_daily_context(target_date)
        context_summary = self.context.build_context_summary(context)

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

    async def answer_question(self, question: str, include_context: bool = True) -> str:
        """
        Answer a user question using available context.

        Args:
            question: User's question
            include_context: Whether to include calendar/notes/email context

        Returns:
            Answer to the question
        """
        messages = []

        # System message
        system_prompt = """You are a helpful personal assistant with access to the user's
calendar, notes, and emails. Answer questions accurately and helpfully based on the
available context. If you don't have enough information, say so clearly."""

        messages.append(self.llm.create_system_message(system_prompt))

        # Add context if requested
        if include_context:
            context = await self.context.build_daily_context()
            context_summary = self.context.build_context_summary(context)
            context_message = f"Current context:\n\n{context_summary}"
            messages.append(self.llm.create_user_message(context_message))

        # Add conversation history
        messages.extend(self.conversation_history[-6:])  # Last 3 exchanges

        # Add current question
        messages.append(self.llm.create_user_message(question))

        # Generate response
        response = await self.llm.generate(messages, temperature=0.7)

        # Update conversation history
        self.conversation_history.append(self.llm.create_user_message(question))
        self.conversation_history.append(self.llm.create_assistant_message(response))

        return response

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
