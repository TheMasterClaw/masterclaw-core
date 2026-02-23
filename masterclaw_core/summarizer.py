"""Conversation summarization service for MasterClaw Core

Provides automatic summarization of chat sessions, key insight extraction,
and intelligent title generation to help users manage long conversations.

Features:
- Generate concise summaries of chat conversations
- Extract key topics, decisions, and action items
- Auto-generate meaningful conversation titles
- Archive conversations with metadata
- Support for different summary types (brief, detailed, bullet points)
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from enum import Enum

from .llm import router as llm_router
from .config import settings

logger = logging.getLogger("masterclaw.summarizer")


class SummaryType(str, Enum):
    """Types of summaries that can be generated"""
    BRIEF = "brief"           # 1-2 sentences
    DETAILED = "detailed"     # Full paragraph
    BULLETS = "bullets"       # Bullet point format
    TOPICS = "topics"         # Key topics only
    ACTIONS = "actions"       # Action items only


@dataclass
class ConversationMessage:
    """A single message in a conversation"""
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationSummary:
    """Result of conversation summarization"""
    session_id: str
    summary: str
    summary_type: SummaryType
    key_topics: List[str] = field(default_factory=list)
    action_items: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)
    sentiment: Optional[str] = None
    message_count: int = 0
    generated_at: datetime = field(default_factory=datetime.utcnow)
    title: Optional[str] = None
    word_count: int = 0
    estimated_reading_time_minutes: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "session_id": self.session_id,
            "summary": self.summary,
            "summary_type": self.summary_type.value,
            "key_topics": self.key_topics,
            "action_items": self.action_items,
            "decisions": self.decisions,
            "sentiment": self.sentiment,
            "message_count": self.message_count,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "title": self.title,
            "word_count": self.word_count,
            "estimated_reading_time_minutes": self.estimated_reading_time_minutes,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationSummary":
        """Create from dictionary"""
        return cls(
            session_id=data["session_id"],
            summary=data["summary"],
            summary_type=SummaryType(data.get("summary_type", "brief")),
            key_topics=data.get("key_topics", []),
            action_items=data.get("action_items", []),
            decisions=data.get("decisions", []),
            sentiment=data.get("sentiment"),
            message_count=data.get("message_count", 0),
            generated_at=datetime.fromisoformat(data["generated_at"]) if data.get("generated_at") else datetime.utcnow(),
            title=data.get("title"),
            word_count=data.get("word_count", 0),
            estimated_reading_time_minutes=data.get("estimated_reading_time_minutes", 0.0),
        )


@dataclass
class ArchiveEntry:
    """An archived conversation with its summary"""
    session_id: str
    original_messages: List[ConversationMessage]
    summary: ConversationSummary
    archived_at: datetime = field(default_factory=datetime.utcnow)
    archive_reason: Optional[str] = None
    compression_ratio: float = 0.0  # How much we reduced the size
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "session_id": self.session_id,
            "original_messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
                    "metadata": msg.metadata,
                }
                for msg in self.original_messages
            ],
            "summary": self.summary.to_dict(),
            "archived_at": self.archived_at.isoformat(),
            "archive_reason": self.archive_reason,
            "compression_ratio": self.compression_ratio,
        }


class SummaryPrompts:
    """Prompt templates for different summary types"""
    
    BRIEF_SUMMARY = """Summarize the following conversation in 1-2 sentences. Be concise and capture the main points:

{conversation}

Summary:"""

    DETAILED_SUMMARY = """Provide a detailed summary of the following conversation. Include context, main discussion points, and outcomes:

{conversation}

Detailed Summary:"""

    BULLET_SUMMARY = """Summarize the following conversation as bullet points. Focus on key information:

{conversation}

Bullet Point Summary:
- """

    TOPIC_EXTRACTION = """Extract the main topics discussed in this conversation. List 3-7 key topics:

{conversation}

Key Topics (one per line):
"""

    ACTION_ITEM_EXTRACTION = """Extract any action items, tasks, or follow-ups from this conversation. If none, say "No action items identified."

{conversation}

Action Items (one per line):
"""

    DECISION_EXTRACTION = """Extract any decisions made or conclusions reached in this conversation:

{conversation}

Decisions/Conclusions (one per line):
"""

    TITLE_GENERATION = """Generate a short, descriptive title (5 words or less) for this conversation:

{conversation}

Title:"""

    SENTIMENT_ANALYSIS = """Analyze the overall sentiment of this conversation (positive, negative, neutral, or mixed). Provide a single word:

{conversation}

Sentiment:"""

    COMPREHENSIVE_SUMMARY = """Analyze the following conversation and provide a structured summary in JSON format.

Conversation:
{conversation}

Provide your analysis in this exact JSON format:
{{
    "summary": "Brief 1-2 sentence overview",
    "key_topics": ["topic1", "topic2", "topic3"],
    "action_items": ["action1", "action2"],
    "decisions": ["decision1"],
    "sentiment": "positive|negative|neutral|mixed",
    "suggested_title": "Short descriptive title"
}}"""


class ConversationSummarizer:
    """
    Summarizes chat conversations using LLM capabilities.
    
    Features:
    - Generate summaries in multiple formats
    - Extract key insights (topics, actions, decisions)
    - Auto-generate conversation titles
    - Archive conversations with metadata
    """
    
    def __init__(self, provider: str = "openai"):
        self.provider = provider
        self._archive: Dict[str, ArchiveEntry] = {}
    
    def _format_conversation(self, messages: List[ConversationMessage]) -> str:
        """Format messages for LLM consumption"""
        formatted = []
        for msg in messages:
            role_label = "User" if msg.role == "user" else "Assistant"
            formatted.append(f"{role_label}: {msg.content}")
        return "\n\n".join(formatted)
    
    def _count_words(self, messages: List[ConversationMessage]) -> int:
        """Count total words in conversation"""
        return sum(len(msg.content.split()) for msg in messages)
    
    async def _call_llm(self, prompt: str, max_tokens: int = 500) -> str:
        """Call LLM with retry logic"""
        try:
            response = await llm_router.chat(
                message=prompt,
                provider=self.provider,
                max_tokens=max_tokens,
                temperature=0.3,  # Lower temperature for consistent summaries
            )
            return response.get("response", "").strip()
        except Exception as e:
            logger.error(f"LLM call failed for summarization: {e}")
            raise
    
    async def summarize(
        self,
        session_id: str,
        messages: List[ConversationMessage],
        summary_type: SummaryType = SummaryType.BRIEF,
        extract_insights: bool = True,
    ) -> ConversationSummary:
        """
        Generate a summary of a conversation.
        
        Args:
            session_id: Unique session identifier
            messages: List of conversation messages
            summary_type: Type of summary to generate
            extract_insights: Whether to extract topics, actions, and decisions
            
        Returns:
            ConversationSummary object with all extracted information
        """
        if not messages:
            return ConversationSummary(
                session_id=session_id,
                summary="No messages to summarize",
                summary_type=summary_type,
                message_count=0,
            )
        
        conversation_text = self._format_conversation(messages)
        word_count = self._count_words(messages)
        
        # Generate main summary
        if summary_type == SummaryType.BRIEF:
            prompt = SummaryPrompts.BRIEF_SUMMARY.format(conversation=conversation_text)
        elif summary_type == SummaryType.DETAILED:
            prompt = SummaryPrompts.DETAILED_SUMMARY.format(conversation=conversation_text)
        elif summary_type == SummaryType.BULLETS:
            prompt = SummaryPrompts.BULLET_SUMMARY.format(conversation=conversation_text)
        else:
            prompt = SummaryPrompts.BRIEF_SUMMARY.format(conversation=conversation_text)
        
        try:
            summary_text = await self._call_llm(prompt, max_tokens=500)
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            summary_text = "Summary generation failed"
        
        # Initialize result
        result = ConversationSummary(
            session_id=session_id,
            summary=summary_text,
            summary_type=summary_type,
            message_count=len(messages),
            word_count=word_count,
            estimated_reading_time_minutes=round(word_count / 200, 1),  # ~200 WPM
        )
        
        # Extract additional insights if requested
        if extract_insights:
            await self._extract_insights(result, conversation_text)
        
        return result
    
    async def _extract_insights(
        self,
        summary: ConversationSummary,
        conversation_text: str,
    ) -> None:
        """Extract topics, actions, decisions, sentiment, and title"""
        
        # Try comprehensive extraction first
        try:
            prompt = SummaryPrompts.COMPREHENSIVE_SUMMARY.format(conversation=conversation_text)
            response = await self._call_llm(prompt, max_tokens=800)
            
            # Parse JSON response
            try:
                # Extract JSON from response (handle markdown code blocks)
                json_str = response
                if "```json" in response:
                    json_str = response.split("```json")[1].split("```")[0]
                elif "```" in response:
                    json_str = response.split("```")[1].split("```")[0]
                
                data = json.loads(json_str.strip())
                
                summary.key_topics = data.get("key_topics", [])
                summary.action_items = data.get("action_items", [])
                summary.decisions = data.get("decisions", [])
                summary.sentiment = data.get("sentiment")
                summary.title = data.get("suggested_title")
                return
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse comprehensive summary JSON: {e}")
        except Exception as e:
            logger.warning(f"Comprehensive extraction failed: {e}")
        
        # Fall back to individual extractions
        await self._extract_individual_insights(summary, conversation_text)
    
    async def _extract_individual_insights(
        self,
        summary: ConversationSummary,
        conversation_text: str,
    ) -> None:
        """Extract insights one at a time (fallback method)"""
        
        # Extract topics
        try:
            prompt = SummaryPrompts.TOPIC_EXTRACTION.format(conversation=conversation_text)
            response = await self._call_llm(prompt, max_tokens=200)
            summary.key_topics = [
                line.strip("- ").strip()
                for line in response.split("\n")
                if line.strip() and not line.startswith("No topics")
            ][:7]  # Limit to 7 topics
        except Exception as e:
            logger.debug(f"Topic extraction failed: {e}")
        
        # Extract action items
        try:
            prompt = SummaryPrompts.ACTION_ITEM_EXTRACTION.format(conversation=conversation_text)
            response = await self._call_llm(prompt, max_tokens=200)
            summary.action_items = [
                line.strip("- ").strip()
                for line in response.split("\n")
                if line.strip() and not line.startswith("No action")
            ]
        except Exception as e:
            logger.debug(f"Action item extraction failed: {e}")
        
        # Extract decisions
        try:
            prompt = SummaryPrompts.DECISION_EXTRACTION.format(conversation=conversation_text)
            response = await self._call_llm(prompt, max_tokens=200)
            summary.decisions = [
                line.strip("- ").strip()
                for line in response.split("\n")
                if line.strip() and not line.startswith("No decisions")
            ]
        except Exception as e:
            logger.debug(f"Decision extraction failed: {e}")
        
        # Analyze sentiment
        try:
            prompt = SummaryPrompts.SENTIMENT_ANALYSIS.format(conversation=conversation_text)
            response = await self._call_llm(prompt, max_tokens=50)
            summary.sentiment = response.split()[0].lower().rstrip(".,")
        except Exception as e:
            logger.debug(f"Sentiment analysis failed: {e}")
        
        # Generate title
        try:
            prompt = SummaryPrompts.TITLE_GENERATION.format(conversation=conversation_text)
            response = await self._call_llm(prompt, max_tokens=50)
            summary.title = response.strip('"').strip("'").strip()
        except Exception as e:
            logger.debug(f"Title generation failed: {e}")
    
    async def generate_title(
        self,
        messages: List[ConversationMessage],
    ) -> Optional[str]:
        """
        Generate a descriptive title for a conversation.
        
        Args:
            messages: List of conversation messages
            
        Returns:
            Generated title or None if generation fails
        """
        if not messages:
            return None
        
        conversation_text = self._format_conversation(messages[:10])  # Use first 10 messages
        
        try:
            prompt = SummaryPrompts.TITLE_GENERATION.format(conversation=conversation_text)
            response = await self._call_llm(prompt, max_tokens=50)
            return response.strip('"').strip("'").strip()
        except Exception as e:
            logger.error(f"Title generation failed: {e}")
            return None
    
    async def archive_conversation(
        self,
        session_id: str,
        messages: List[ConversationMessage],
        summary_type: SummaryType = SummaryType.DETAILED,
        archive_reason: Optional[str] = None,
    ) -> ArchiveEntry:
        """
        Archive a conversation with its summary.
        
        Args:
            session_id: Unique session identifier
            messages: List of conversation messages
            summary_type: Type of summary to generate
            archive_reason: Reason for archiving (e.g., "age", "size", "manual")
            
        Returns:
            ArchiveEntry with summary and metadata
        """
        # Generate summary
        summary = await self.summarize(
            session_id=session_id,
            messages=messages,
            summary_type=summary_type,
            extract_insights=True,
        )
        
        # Calculate compression ratio
        original_word_count = self._count_words(messages)
        summary_word_count = len(summary.summary.split())
        compression_ratio = (
            (original_word_count - summary_word_count) / original_word_count
            if original_word_count > 0 else 0.0
        )
        
        # Create archive entry
        archive = ArchiveEntry(
            session_id=session_id,
            original_messages=messages,
            summary=summary,
            archive_reason=archive_reason,
            compression_ratio=compression_ratio,
        )
        
        # Store in memory archive
        self._archive[session_id] = archive
        
        logger.info(
            f"Archived session {session_id}: {len(messages)} messages, "
            f"{compression_ratio:.1%} compression"
        )
        
        return archive
    
    def get_archive(self, session_id: str) -> Optional[ArchiveEntry]:
        """Retrieve an archived conversation"""
        return self._archive.get(session_id)
    
    def list_archives(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ArchiveEntry]:
        """List archived conversations"""
        archives = list(self._archive.values())
        archives.sort(key=lambda x: x.archived_at, reverse=True)
        return archives[offset:offset + limit]
    
    def clear_archive(self, session_id: Optional[str] = None) -> int:
        """
        Clear archived conversations.
        
        Args:
            session_id: Specific session to clear, or None to clear all
            
        Returns:
            Number of archives cleared
        """
        if session_id:
            if session_id in self._archive:
                del self._archive[session_id]
                return 1
            return 0
        else:
            count = len(self._archive)
            self._archive.clear()
            return count


# Global summarizer instance
summarizer = ConversationSummarizer()
