"""MasterClaw Agent Chat Interface - WebSocket-based multi-agent communication system

This module provides real-time bidirectional communication between Rex and agents,
enabling direct chat, agent orchestration, and memory persistence.

Features:
- WebSocket-based real-time chat with agents
- Agent presence and status tracking
- Message routing to specific agents or broadcasts
- Agent memory persistence (thoughts, jobs, desires, blockers)
- Multi-agent swarm coordination
- Typing indicators and read receipts
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field, asdict

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("masterclaw.agent_chat")


class AgentStatus(str, Enum):
    """Agent connection and operational status"""
    ONLINE = "online"
    BUSY = "busy"
    AWAY = "away"
    OFFLINE = "offline"
    ERROR = "error"


class MessageType(str, Enum):
    """Types of messages in the agent chat system"""
    # User <-> Agent messages
    USER_MESSAGE = "user_message"
    AGENT_MESSAGE = "agent_message"
    
    # Agent status and presence
    STATUS_UPDATE = "status_update"
    TYPING_INDICATOR = "typing_indicator"
    READ_RECEIPT = "read_receipt"
    
    # Agent memory/logging
    AGENT_THOUGHT = "agent_thought"
    AGENT_JOB_STARTED = "agent_job_started"
    AGENT_JOB_COMPLETED = "agent_job_completed"
    AGENT_DESIRE = "agent_desire"
    AGENT_BLOCKER = "agent_blocker"
    
    # System messages
    SYSTEM_NOTICE = "system_notice"
    ERROR_MESSAGE = "error_message"
    
    # Swarm coordination
    SWARM_FORMED = "swarm_formed"
    SWARM_DISBANDED = "swarm_disbanded"
    AGENT_HANDOFF = "agent_handoff"


class JobStatus(str, Enum):
    """Status of an agent's job"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentJob:
    """Represents a job/task assigned to an agent"""
    job_id: str
    agent_id: str
    title: str
    description: str
    status: JobStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "agent_id": self.agent_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "metadata": self.metadata,
        }


@dataclass
class AgentDesire:
    """Represents something an agent needs or wants"""
    desire_id: str
    agent_id: str
    description: str
    priority: str  # high, medium, low
    created_at: datetime
    fulfilled_at: Optional[datetime] = None
    fulfilled_by: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "desire_id": self.desire_id,
            "agent_id": self.agent_id,
            "description": self.description,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "fulfilled_at": self.fulfilled_at.isoformat() if self.fulfilled_at else None,
            "fulfilled_by": self.fulfilled_by,
        }


@dataclass
class AgentBlocker:
    """Represents a blocker preventing an agent from proceeding"""
    blocker_id: str
    agent_id: str
    description: str
    severity: str  # critical, high, medium, low
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "blocker_id": self.blocker_id,
            "agent_id": self.agent_id,
            "description": self.description,
            "severity": self.severity,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "resolution": self.resolution,
        }


@dataclass
class AgentThought:
    """Represents an agent's internal thought or reasoning"""
    thought_id: str
    agent_id: str
    thought: str
    context: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    related_job_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "thought_id": self.thought_id,
            "agent_id": self.agent_id,
            "thought": self.thought,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "related_job_id": self.related_job_id,
        }


@dataclass
class AgentInfo:
    """Information about a connected agent"""
    agent_id: str
    name: str
    role: str
    status: AgentStatus
    capabilities: List[str]
    connected_at: datetime
    last_activity: datetime
    websocket: Optional[WebSocket] = None
    current_job: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Memory stores
    thoughts: List[AgentThought] = field(default_factory=list)
    jobs: List[AgentJob] = field(default_factory=list)
    desires: List[AgentDesire] = field(default_factory=list)
    blockers: List[AgentBlocker] = field(default_factory=list)
    
    def to_dict(self, include_memory: bool = False) -> Dict[str, Any]:
        data = {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "status": self.status.value,
            "capabilities": self.capabilities,
            "connected_at": self.connected_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "current_job": self.current_job,
            "metadata": self.metadata,
        }
        
        if include_memory:
            data["thoughts"] = [t.to_dict() for t in self.thoughts[-10:]]  # Last 10
            data["jobs"] = [j.to_dict() for j in self.jobs[-5:]]  # Last 5
            data["desires"] = [d.to_dict() for d in self.desires if not d.fulfilled_at]
            data["blockers"] = [b.to_dict() for b in self.blockers if not b.resolved_at]
        
        return data


@dataclass
class ChatMessage:
    """A message in the agent chat system"""
    message_id: str
    message_type: MessageType
    sender_id: str
    sender_name: str
    recipient_id: Optional[str]  # None = broadcast
    content: str
    timestamp: datetime
    conversation_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "recipient_id": self.recipient_id,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "conversation_id": self.conversation_id,
            "metadata": self.metadata,
        }


@dataclass
class SwarmInfo:
    """Information about an agent swarm"""
    swarm_id: str
    name: str
    leader_id: str
    member_ids: List[str]
    formed_at: datetime
    status: str  # active, paused, disbanded
    goal: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "swarm_id": self.swarm_id,
            "name": self.name,
            "leader_id": self.leader_id,
            "member_ids": self.member_ids,
            "formed_at": self.formed_at.isoformat(),
            "status": self.status,
            "goal": self.goal,
        }


class AgentChatManager:
    """
    Manages WebSocket connections for agent chat.
    
    Handles:
    - Agent connections/disconnections
    - Message routing
    - Presence tracking
    - Agent memory persistence
    - Swarm coordination
    """
    
    def __init__(self):
        # Connected agents: agent_id -> AgentInfo
        self.agents: Dict[str, AgentInfo] = {}
        
        # User connections: user_id -> WebSocket
        self.users: Dict[str, WebSocket] = {}
        
        # Message history by conversation
        self.conversations: Dict[str, List[ChatMessage]] = {}
        
        # Active swarms
        self.swarms: Dict[str, SwarmInfo] = {}
        
        # Typing indicators: conversation_id -> {sender_id: timestamp}
        self.typing: Dict[str, Dict[str, float]] = {}
        
        # Callbacks for message handling
        self.message_handlers: List[Callable[[ChatMessage], None]] = []
        
        logger.info("AgentChatManager initialized")
    
    async def connect_agent(
        self,
        websocket: WebSocket,
        agent_id: str,
        name: str,
        role: str,
        capabilities: List[str] = None,
        metadata: Dict[str, Any] = None,
    ) -> AgentInfo:
        """
        Register a new agent connection.
        
        Args:
            websocket: The WebSocket connection
            agent_id: Unique agent identifier
            name: Display name
            role: Agent role (e.g., "coder", "reviewer", "architect")
            capabilities: List of capability strings
            metadata: Additional agent metadata
            
        Returns:
            AgentInfo for the connected agent
        """
        now = datetime.utcnow()
        
        agent = AgentInfo(
            agent_id=agent_id,
            name=name,
            role=role,
            status=AgentStatus.ONLINE,
            capabilities=capabilities or [],
            connected_at=now,
            last_activity=now,
            websocket=websocket,
            metadata=metadata or {},
        )
        
        self.agents[agent_id] = agent
        
        # Notify all users of new agent
        await self._broadcast_to_users({
            "type": "agent_connected",
            "agent": agent.to_dict(),
        })
        
        logger.info(f"Agent connected: {name} ({agent_id}) as {role}")
        return agent
    
    async def connect_user(self, user_id: str, websocket: WebSocket) -> None:
        """Register a new user connection (Rex)"""
        self.users[user_id] = websocket
        
        # Send list of available agents
        agents_list = [
            agent.to_dict(include_memory=False)
            for agent in self.agents.values()
        ]
        
        await websocket.send_json({
            "type": "connection_established",
            "user_id": user_id,
            "available_agents": agents_list,
            "active_swarms": [s.to_dict() for s in self.swarms.values()],
        })
        
        logger.info(f"User connected: {user_id}")
    
    async def disconnect_agent(self, agent_id: str) -> None:
        """Handle agent disconnection"""
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            agent.status = AgentStatus.OFFLINE
            agent.websocket = None
            
            # Keep agent info but mark offline
            # Notify users
            await self._broadcast_to_users({
                "type": "agent_disconnected",
                "agent_id": agent_id,
                "agent_name": agent.name,
            })
            
            logger.info(f"Agent disconnected: {agent.name} ({agent_id})")
    
    async def disconnect_user(self, user_id: str) -> None:
        """Handle user disconnection"""
        if user_id in self.users:
            del self.users[user_id]
            logger.info(f"User disconnected: {user_id}")
    
    async def send_message(
        self,
        sender_id: str,
        sender_name: str,
        content: str,
        message_type: MessageType = MessageType.USER_MESSAGE,
        recipient_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        metadata: Dict[str, Any] = None,
    ) -> ChatMessage:
        """
        Send a message in the chat system.
        
        Args:
            sender_id: ID of sender (user or agent)
            sender_name: Display name of sender
            content: Message content
            message_type: Type of message
            recipient_id: Target agent (None = broadcast to all)
            conversation_id: Conversation thread ID
            metadata: Additional message metadata
            
        Returns:
            The created ChatMessage
        """
        message = ChatMessage(
            message_id=str(uuid.uuid4()),
            message_type=message_type,
            sender_id=sender_id,
            sender_name=sender_name,
            recipient_id=recipient_id,
            content=content,
            timestamp=datetime.utcnow(),
            conversation_id=conversation_id or "default",
            metadata=metadata or {},
        )
        
        # Store in conversation history
        if message.conversation_id not in self.conversations:
            self.conversations[message.conversation_id] = []
        self.conversations[message.conversation_id].append(message)
        
        # Limit history size
        if len(self.conversations[message.conversation_id]) > 1000:
            self.conversations[message.conversation_id] = self.conversations[message.conversation_id][-1000:]
        
        # Route message
        if recipient_id:
            # Direct message to specific agent
            if recipient_id in self.agents:
                agent = self.agents[recipient_id]
                if agent.websocket:
                    await agent.websocket.send_json({
                        "type": "message",
                        "message": message.to_dict(),
                    })
        else:
            # Broadcast to all agents
            await self._broadcast_to_agents({
                "type": "message",
                "message": message.to_dict(),
            })
        
        # Also send to sender's user connection if applicable
        if sender_id in self.users:
            await self.users[sender_id].send_json({
                "type": "message_sent",
                "message": message.to_dict(),
            })
        
        # Trigger callbacks
        for handler in self.message_handlers:
            try:
                handler(message)
            except Exception as e:
                logger.error(f"Message handler error: {e}")
        
        return message
    
    async def update_agent_status(
        self,
        agent_id: str,
        status: AgentStatus,
        current_job: Optional[str] = None,
    ) -> None:
        """Update an agent's status"""
        if agent_id not in self.agents:
            return
        
        agent = self.agents[agent_id]
        agent.status = status
        agent.last_activity = datetime.utcnow()
        if current_job:
            agent.current_job = current_job
        
        # Notify users
        await self._broadcast_to_users({
            "type": "agent_status_update",
            "agent_id": agent_id,
            "status": status.value,
            "current_job": current_job,
        })
    
    async def set_typing_indicator(
        self,
        sender_id: str,
        conversation_id: str,
        is_typing: bool,
    ) -> None:
        """Set typing indicator for a conversation"""
        if conversation_id not in self.typing:
            self.typing[conversation_id] = {}
        
        if is_typing:
            self.typing[conversation_id][sender_id] = time.time()
        else:
            self.typing[conversation_id].pop(sender_id, None)
        
        # Broadcast typing status
        await self._broadcast({
            "type": "typing_indicator",
            "conversation_id": conversation_id,
            "sender_id": sender_id,
            "is_typing": is_typing,
        })
    
    # ========================================================================
    # Agent Memory Methods
    # ========================================================================
    
    def log_agent_thought(
        self,
        agent_id: str,
        thought: str,
        context: Optional[str] = None,
        related_job_id: Optional[str] = None,
    ) -> AgentThought:
        """Log an agent's thought for memory"""
        if agent_id not in self.agents:
            logger.warning(f"Cannot log thought for unknown agent: {agent_id}")
            return None
        
        thought_obj = AgentThought(
            thought_id=str(uuid.uuid4()),
            agent_id=agent_id,
            thought=thought,
            context=context,
            related_job_id=related_job_id,
        )
        
        self.agents[agent_id].thoughts.append(thought_obj)
        
        # Keep only last 100 thoughts
        if len(self.agents[agent_id].thoughts) > 100:
            self.agents[agent_id].thoughts = self.agents[agent_id].thoughts[-100:]
        
        logger.debug(f"Agent {agent_id} thought logged: {thought[:50]}...")
        return thought_obj
    
    def start_agent_job(
        self,
        agent_id: str,
        title: str,
        description: str,
        metadata: Dict[str, Any] = None,
    ) -> AgentJob:
        """Record that an agent started a job"""
        if agent_id not in self.agents:
            logger.warning(f"Cannot start job for unknown agent: {agent_id}")
            return None
        
        job = AgentJob(
            job_id=str(uuid.uuid4()),
            agent_id=agent_id,
            title=title,
            description=description,
            status=JobStatus.IN_PROGRESS,
            started_at=datetime.utcnow(),
            metadata=metadata or {},
        )
        
        self.agents[agent_id].jobs.append(job)
        self.agents[agent_id].current_job = job.job_id
        
        # Keep only last 50 jobs
        if len(self.agents[agent_id].jobs) > 50:
            self.agents[agent_id].jobs = self.agents[agent_id].jobs[-50:]
        
        logger.info(f"Agent {agent_id} started job: {title}")
        return job
    
    def complete_agent_job(
        self,
        agent_id: str,
        job_id: str,
        result: str,
        status: JobStatus = JobStatus.COMPLETED,
    ) -> None:
        """Mark an agent job as completed"""
        if agent_id not in self.agents:
            return
        
        agent = self.agents[agent_id]
        for job in agent.jobs:
            if job.job_id == job_id:
                job.status = status
                job.completed_at = datetime.utcnow()
                job.result = result
                break
        
        if agent.current_job == job_id:
            agent.current_job = None
        
        logger.info(f"Agent {agent_id} completed job: {job_id}")
    
    def add_agent_desire(
        self,
        agent_id: str,
        description: str,
        priority: str = "medium",
    ) -> AgentDesire:
        """Record something an agent needs"""
        if agent_id not in self.agents:
            logger.warning(f"Cannot add desire for unknown agent: {agent_id}")
            return None
        
        desire = AgentDesire(
            desire_id=str(uuid.uuid4()),
            agent_id=agent_id,
            description=description,
            priority=priority,
            created_at=datetime.utcnow(),
        )
        
        self.agents[agent_id].desires.append(desire)
        
        # Notify users of agent desire
        asyncio.create_task(self._broadcast_to_users({
            "type": "agent_desire",
            "agent_id": agent_id,
            "desire": desire.to_dict(),
        }))
        
        logger.info(f"Agent {agent_id} expressed desire: {description}")
        return desire
    
    def fulfill_agent_desire(
        self,
        agent_id: str,
        desire_id: str,
        fulfilled_by: str,
    ) -> None:
        """Mark an agent desire as fulfilled"""
        if agent_id not in self.agents:
            return
        
        for desire in self.agents[agent_id].desires:
            if desire.desire_id == desire_id:
                desire.fulfilled_at = datetime.utcnow()
                desire.fulfilled_by = fulfilled_by
                break
    
    def add_agent_blocker(
        self,
        agent_id: str,
        description: str,
        severity: str = "high",
    ) -> AgentBlocker:
        """Record a blocker preventing an agent from proceeding"""
        if agent_id not in self.agents:
            logger.warning(f"Cannot add blocker for unknown agent: {agent_id}")
            return None
        
        blocker = AgentBlocker(
            blocker_id=str(uuid.uuid4()),
            agent_id=agent_id,
            description=description,
            severity=severity,
            created_at=datetime.utcnow(),
        )
        
        self.agents[agent_id].blockers.append(blocker)
        
        # Notify users of blocker (important!)
        asyncio.create_task(self._broadcast_to_users({
            "type": "agent_blocker",
            "agent_id": agent_id,
            "blocker": blocker.to_dict(),
        }))
        
        logger.warning(f"Agent {agent_id} blocked: {description}")
        return blocker
    
    def resolve_agent_blocker(
        self,
        agent_id: str,
        blocker_id: str,
        resolved_by: str,
        resolution: str,
    ) -> None:
        """Mark an agent blocker as resolved"""
        if agent_id not in self.agents:
            return
        
        for blocker in self.agents[agent_id].blockers:
            if blocker.blocker_id == blocker_id:
                blocker.resolved_at = datetime.utcnow()
                blocker.resolved_by = resolved_by
                blocker.resolution = resolution
                
                # Notify users
                asyncio.create_task(self._broadcast_to_users({
                    "type": "blocker_resolved",
                    "agent_id": agent_id,
                    "blocker_id": blocker_id,
                    "resolution": resolution,
                }))
                break
    
    # ========================================================================
    # Swarm Management
    # ========================================================================
    
    async def form_swarm(
        self,
        name: str,
        leader_id: str,
        member_ids: List[str],
        goal: Optional[str] = None,
    ) -> SwarmInfo:
        """Form a new agent swarm"""
        swarm = SwarmInfo(
            swarm_id=str(uuid.uuid4()),
            name=name,
            leader_id=leader_id,
            member_ids=member_ids,
            formed_at=datetime.utcnow(),
            status="active",
            goal=goal,
        )
        
        self.swarms[swarm.swarm_id] = swarm
        
        # Notify all
        await self._broadcast({
            "type": "swarm_formed",
            "swarm": swarm.to_dict(),
        })
        
        logger.info(f"Swarm formed: {name} ({swarm.swarm_id}) with {len(member_ids)} members")
        return swarm
    
    async def disband_swarm(self, swarm_id: str) -> None:
        """Disband a swarm"""
        if swarm_id not in self.swarms:
            return
        
        swarm = self.swarms[swarm_id]
        swarm.status = "disbanded"
        
        await self._broadcast({
            "type": "swarm_disbanded",
            "swarm_id": swarm_id,
        })
        
        del self.swarms[swarm_id]
        logger.info(f"Swarm disbanded: {swarm.name} ({swarm_id})")
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    async def _broadcast_to_agents(self, message: Dict[str, Any]) -> None:
        """Send message to all connected agents"""
        for agent in self.agents.values():
            if agent.websocket:
                try:
                    await agent.websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to send to agent {agent.agent_id}: {e}")
    
    async def _broadcast_to_users(self, message: Dict[str, Any]) -> None:
        """Send message to all connected users"""
        for user_id, websocket in self.users.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send to user {user_id}: {e}")
    
    async def _broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast to both agents and users"""
        await self._broadcast_to_agents(message)
        await self._broadcast_to_users(message)
    
    def get_agent_memory(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get full memory for an agent"""
        if agent_id not in self.agents:
            return None
        
        agent = self.agents[agent_id]
        return {
            "agent_id": agent_id,
            "thoughts": [t.to_dict() for t in agent.thoughts],
            "jobs": [j.to_dict() for j in agent.jobs],
            "desires": [d.to_dict() for d in agent.desires],
            "blockers": [b.to_dict() for b in agent.blockers if not b.resolved_at],
        }
    
    def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get message history for a conversation"""
        messages = self.conversations.get(conversation_id, [])
        return [m.to_dict() for m in messages[-limit:]]
    
    def on_message(self, handler: Callable[[ChatMessage], None]) -> Callable:
        """Register a message handler callback"""
        self.message_handlers.append(handler)
        return handler


# Global agent chat manager instance
agent_chat = AgentChatManager()
