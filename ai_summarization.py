#!/usr/bin/env python3
"""
AI-Powered Message Summarization
Automatically summarizes long discussion threads using OpenAI API

Features:
- Auto-summarize when message count exceeds threshold
- Channel-specific summaries
- Key decision extraction
- Action items identification
- Participant activity summary
"""
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class MessageSummary:
    """Summary of a message thread"""

    channel: str
    message_count: int
    time_range: str
    summary: str
    key_decisions: List[str]
    action_items: List[str]
    top_contributors: List[Dict[str, int]]  # [{client_id: message_count}]
    generated_at: str


class AISummarizer:
    """
    AI-powered message summarization

    Features:
    - Automatic summarization when threshold reached
    - OpenAI GPT-4 for high-quality summaries
    - Extracts decisions and action items
    - Tracks participant activity
    """

    def __init__(
        self, auto_summarize_threshold: int = 50, summary_length: str = "concise"
    ):
        """
        Args:
            auto_summarize_threshold: Message count before auto-summary
            summary_length: "brie" (3-5 sentences), "concise" (1-2 paragraphs), "detailed" (3+ paragraphs)
        """
        self.auto_summarize_threshold = auto_summarize_threshold
        self.summary_length = summary_length

        # Cache summaries to avoid re-summarizing
        self.summary_cache: Dict[str, MessageSummary] = {}  # channel -> last summary

        # Track message counts per channel
        self.message_counts: Dict[str, int] = defaultdict(int)

    def should_summarize(self, channel: str, message_count: int) -> bool:
        """
        Check if channel should be summarized

        Args:
            channel: Channel ID
            message_count: Current message count

        Returns:
            True if summarization needed
        """
        # Get last summary count
        last_summary = self.summary_cache.get(channel)
        if not last_summary:
            # Never summarized
            return message_count >= self.auto_summarize_threshold

        # Summarize if threshold messages since last summary
        messages_since_last = message_count - last_summary.message_count
        return messages_since_last >= self.auto_summarize_threshold

    def summarize_messages(
        self, messages: List[Dict], channel: str = "main", use_ai: bool = True
    ) -> MessageSummary:
        """
        Summarize message thread

        Args:
            messages: List of message dicts with 'from', 'text', 'timestamp'
            channel: Channel ID
            use_ai: Use OpenAI API (True) or simple extraction (False)

        Returns:
            MessageSummary with summary, decisions, action items
        """
        if not messages:
            return MessageSummary(
                channel=channel,
                message_count=0,
                time_range="",
                summary="No messages to summarize.",
                key_decisions=[],
                action_items=[],
                top_contributors=[],
                generated_at=datetime.now(timezone.utc).isoformat(),
            )

        # Extract metadata
        message_count = len(messages)
        time_range = f"{messages[0]['timestamp']} to {messages[-1]['timestamp']}"

        # Count participants
        participant_counts = defaultdict(int)
        for msg in messages:
            participant_counts[msg["from_client"]] += 1

        top_contributors = [
            {client: count}
            for client, count in sorted(
                participant_counts.items(), key=lambda x: x[1], reverse=True
            )[:5]
        ]

        if use_ai:
            # Use OpenAI API for intelligent summarization
            summary_result = self._summarize_with_ai(messages, channel)
        else:
            # Simple extraction without AI
            summary_result = self._summarize_simple(messages)

        result = MessageSummary(
            channel=channel,
            message_count=message_count,
            time_range=time_range,
            summary=summary_result["summary"],
            key_decisions=summary_result["decisions"],
            action_items=summary_result["action_items"],
            top_contributors=top_contributors,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

        # Cache summary
        self.summary_cache[channel] = result
        self.message_counts[channel] = message_count

        return result

    def _summarize_with_ai(self, messages: List[Dict], channel: str) -> Dict:
        """
        Use OpenAI API to generate intelligent summary

        Args:
            messages: Message list
            channel: Channel ID

        Returns:
            Dict with 'summary', 'decisions', 'action_items'
        """
        # Format messages for AI
        conversation = []
        for msg in messages:
            conversation.append(f"{msg['from_client']}: {msg['text']}")

        conversation_text = "\n".join(conversation)

        # Determine length instruction
        length_instructions = {
            "brie": "Summarize in 3-5 sentences.",
            "concise": "Summarize in 1-2 paragraphs.",
            "detailed": "Provide a detailed summary in 3+ paragraphs.",
        }
        length_instruction = length_instructions.get(
            self.summary_length, length_instructions["concise"]
        )

        # Create prompt
        prompt = """Analyze this collaboration room discussion and provide:

1. **Summary**: {length_instruction}
2. **Key Decisions**: List any decisions made (voting results, consensus reached)
3. **Action Items**: List any tasks or next steps mentioned

Discussion from channel '{channel}':
---
{conversation_text}
---

Format your response as JSON:
{{
  "summary": "...",
  "decisions": ["decision 1", "decision 2", ...],
  "action_items": ["action 1", "action 2", ...]
}}"""

        try:
            # Use OpenAI Bridge MCP for real AI summarization
            import sys
            import os

            # Try to use openai-bridge MCP if available
            try:
                # Import MCP function directly - available in Claude Code environment
                from mcp import openai_chat_json

                response = openai_chat_json(
                    prompt=prompt,
                    model="gpt-4o-mini",  # Cost-effective for summaries
                    max_tokens=800,
                    temperature=0.3,  # Lower temperature for factual summaries
                )

                # Parse JSON response
                result = json.loads(response) if isinstance(response, str) else response

                logger.info(
                    f"✅ Generated AI summary using GPT-4o-mini for {len(messages)} messages in channel '{channel}'"
                )

                return {
                    "summary": result.get("summary", ""),
                    "decisions": result.get("decisions", []),
                    "action_items": result.get("action_items", []),
                }

            except ImportError:
                # MCP not available, try direct OpenAI API
                logger.warning("OpenAI MCP not available, trying direct API")

                import openai

                api_key = os.getenv("OPENAI_API_KEY")

                if not api_key:
                    logger.error(
                        "❌ OPENAI_API_KEY environment variable not set. AI summarization unavailable."
                    )
                    logger.error("   Set the API key: export OPENAI_API_KEY=sk-...")
                    raise ValueError(
                        "OpenAI API key required for AI summarization. Set OPENAI_API_KEY environment variable."
                    )

                client = openai.OpenAI(api_key=api_key)

                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a helpful assistant that summarizes collaboration discussions. Always respond with valid JSON.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=800,
                    temperature=0.3,
                )

                result = json.loads(response.choices[0].message.content)

                logger.info(
                    f"✅ Generated AI summary using OpenAI API for {len(messages)} messages in channel '{channel}'"
                )

                return {
                    "summary": result.get("summary", ""),
                    "decisions": result.get("decisions", []),
                    "action_items": result.get("action_items", []),
                }

        except Exception as e:
            logger.error(
                f"AI summarization failed: {e}, falling back to simple extraction"
            )
            return self._summarize_simple(messages)

    def _summarize_simple(self, messages: List[Dict]) -> Dict:
        """
        Simple extraction without AI

        Args:
            messages: Message list

        Returns:
            Dict with 'summary', 'decisions', 'action_items'
        """
        summary = self._extract_simple_summary(messages)
        decisions = self._extract_decisions(messages)
        actions = self._extract_action_items(messages)

        return {"summary": summary, "decisions": decisions, "action_items": actions}

    def _extract_simple_summary(self, messages: List[Dict]) -> str:
        """Extract simple summary from messages"""
        if not messages:
            return "No discussion."

        # Get unique participants
        participants = set(msg["from_client"] for msg in messages)

        # Count message types
        code_messages = sum(1 for msg in messages if "code" in msg.get("type", ""))
        file_messages = sum(1 for msg in messages if "file" in msg.get("type", ""))

        summary_parts = [
            f"{len(messages)} messages from {len(participants)} participants."
        ]

        if code_messages > 0:
            summary_parts.append(f"{code_messages} code executions.")
        if file_messages > 0:
            summary_parts.append(f"{file_messages} files shared.")

        return " ".join(summary_parts)

    def _extract_decisions(self, messages: List[Dict]) -> List[str]:
        """Extract decisions from messages"""
        decisions = []

        decision_keywords = ["approved", "consensus", "voted", "decided", "agreed"]

        for msg in messages:
            text = msg.get("text", "").lower()
            if any(keyword in text for keyword in decision_keywords):
                # Found potential decision
                decisions.append(f"{msg['from_client']}: {msg['text'][:100]}")

        return decisions[:10]  # Limit to 10 decisions

    def _extract_action_items(self, messages: List[Dict]) -> List[str]:
        """Extract action items from messages"""
        action_items = []

        action_keywords = [
            "todo",
            "task",
            "action item",
            "need to",
            "should",
            "will",
            "going to",
        ]

        for msg in messages:
            text = msg.get("text", "").lower()
            if any(keyword in text for keyword in action_keywords):
                # Found potential action item
                action_items.append(f"{msg['from_client']}: {msg['text'][:100]}")

        return action_items[:15]  # Limit to 15 action items

    def format_summary(self, summary: MessageSummary, format: str = "text") -> str:
        """
        Format summary for display

        Args:
            summary: MessageSummary object
            format: "text" or "markdown"

        Returns:
            Formatted summary string
        """
        if format == "markdown":
            lines = [
                f"# 📝 Channel Summary: {summary.channel}",
                "",
                f"**Messages**: {summary.message_count}",
                f"**Time Range**: {summary.time_range}",
                f"**Generated**: {summary.generated_at}",
                "",
                "## Summary",
                summary.summary,
                "",
            ]

            if summary.key_decisions:
                lines.append("## 🎯 Key Decisions")
                for i, decision in enumerate(summary.key_decisions, 1):
                    lines.append(f"{i}. {decision}")
                lines.append("")

            if summary.action_items:
                lines.append("## ✅ Action Items")
                for i, item in enumerate(summary.action_items, 1):
                    lines.append(f"{i}. {item}")
                lines.append("")

            if summary.top_contributors:
                lines.append("## 👥 Top Contributors")
                for contributor in summary.top_contributors:
                    for client, count in contributor.items():
                        lines.append(f"- {client}: {count} messages")
                lines.append("")

            return "\n".join(lines)

        else:  # text format
            lines = [
                f"📝 CHANNEL SUMMARY: {summary.channel}",
                f"Messages: {summary.message_count} | Time: {summary.time_range}",
                "",
                "Summary:",
                summary.summary,
                "",
            ]

            if summary.key_decisions:
                lines.append("Key Decisions:")
                for decision in summary.key_decisions:
                    lines.append(f"  • {decision}")
                lines.append("")

            if summary.action_items:
                lines.append("Action Items:")
                for item in summary.action_items:
                    lines.append(f"  ✓ {item}")
                lines.append("")

            if summary.top_contributors:
                lines.append("Top Contributors:")
                for contributor in summary.top_contributors:
                    for client, count in contributor.items():
                        lines.append(f"  - {client}: {count} messages")

            return "\n".join(lines)

    def export_summary(self, summary: MessageSummary, filepath: str):
        """
        Export summary to JSON file

        Args:
            summary: MessageSummary object
            filepath: Output file path
        """
        with open(filepath, "w") as f:
            json.dump(asdict(summary), f, indent=2)

        logger.info(f"Summary exported to {filepath}")


# Example usage
if __name__ == "__main__":
    print("=" * 80)
    print("🤖 AI Message Summarization - Test")
    print("=" * 80)

    summarizer = AISummarizer(auto_summarize_threshold=10, summary_length="concise")

    # Sample messages
    messages = [
        {
            "from_client": "claude-code",
            "text": "Let's build a trading bot",
            "timestamp": "2026-02-22T10:00:00Z",
        },
        {
            "from_client": "claude-desktop-1",
            "text": "I agree! Should we use FastAPI?",
            "timestamp": "2026-02-22T10:01:00Z",
        },
        {
            "from_client": "claude-desktop-2",
            "text": "FastAPI sounds good. I can handle the database layer.",
            "timestamp": "2026-02-22T10:02:00Z",
        },
        {
            "from_client": "claude-code",
            "text": "Voted: Use FastAPI - APPROVED",
            "timestamp": "2026-02-22T10:03:00Z",
        },
        {
            "from_client": "claude-desktop-1",
            "text": "TODO: Set up FastAPI project structure",
            "timestamp": "2026-02-22T10:04:00Z",
        },
        {
            "from_client": "claude-desktop-2",
            "text": "I will create the SQLAlchemy models",
            "timestamp": "2026-02-22T10:05:00Z",
        },
        {
            "from_client": "claude-code",
            "text": "Action item: Write API documentation",
            "timestamp": "2026-02-22T10:06:00Z",
        },
    ]

    print(f"\n📨 Processing {len(messages)} messages...")

    # Check if should summarize
    should_summarize = summarizer.should_summarize("main", len(messages))
    print(
        f"Should summarize (threshold={summarizer.auto_summarize_threshold}): {should_summarize}"
    )

    # Generate summary
    summary = summarizer.summarize_messages(messages, channel="main", use_ai=False)

    print("\n" + "=" * 80)
    print(summarizer.format_summary(summary, format="text"))
    print("=" * 80)

    # Export to JSON
    summarizer.export_summary(summary, "test_summary.json")
    print("\n✅ Summary exported to test_summary.json")

    # Test auto-summarize check
    print("\n📊 Message count tracking:")
    print(f"   main: {summarizer.message_counts['main']} messages")
    print(
        f"   Should summarize again with 5 more messages: {summarizer.should_summarize('main', len(messages) + 5)}"
    )

    print("\n✅ AI Summarization test complete!")
