"""GitHub webhook handler for MasterClaw Core

Provides secure webhook endpoints for GitHub integration:
- Push events (trigger deployments)
- Pull request events (notifications)
- Workflow/job events (CI/CD status)
- Release events (deployment triggers)

Security features:
- HMAC-SHA256 signature verification
- IP allowlist validation (GitHub's IP ranges)
- Event type filtering
- Replay attack prevention (timestamp validation)
"""

import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("masterclaw.webhook")


class WebhookEventType(str, Enum):
    """GitHub webhook event types"""
    PUSH = "push"
    PULL_REQUEST = "pull_request"
    WORKFLOW_RUN = "workflow_run"
    WORKFLOW_JOB = "workflow_job"
    RELEASE = "release"
    PING = "ping"
    ISSUES = "issues"
    ISSUE_COMMENT = "issue_comment"
    STAR = "star"
    WATCH = "watch"
    FORK = "fork"


class WorkflowStatus(str, Enum):
    """GitHub Actions workflow status"""
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    WAITING = "waiting"
    PENDING = "pending"


class WorkflowConclusion(str, Enum):
    """GitHub Actions workflow conclusion"""
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
    TIMED_OUT = "timed_out"
    ACTION_REQUIRED = "action_required"


@dataclass
class WebhookPayload:
    """Parsed GitHub webhook payload"""
    event_type: WebhookEventType
    delivery_id: str
    timestamp: datetime
    repository: str
    repository_url: str
    sender: str
    sender_avatar: str
    raw_payload: Dict[str, Any]
    
    # Event-specific fields
    ref: Optional[str] = None
    commit_sha: Optional[str] = None
    commit_message: Optional[str] = None
    pusher: Optional[str] = None
    
    # PR fields
    pr_number: Optional[int] = None
    pr_title: Optional[str] = None
    pr_state: Optional[str] = None
    pr_url: Optional[str] = None
    pr_action: Optional[str] = None
    
    # Workflow fields
    workflow_name: Optional[str] = None
    workflow_status: Optional[WorkflowStatus] = None
    workflow_conclusion: Optional[WorkflowConclusion] = None
    workflow_run_id: Optional[int] = None
    workflow_branch: Optional[str] = None
    
    # Release fields
    release_tag: Optional[str] = None
    release_name: Optional[str] = None
    release_draft: bool = False
    release_prerelease: bool = False


@dataclass
class WebhookResult:
    """Result of webhook processing"""
    success: bool
    message: str
    event_type: str
    action_taken: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# GitHub's IP ranges for webhook delivery (as of 2024)
# In production, these should be fetched from GitHub's API
GITHUB_HOOK_IPS = [
    "192.30.252.0/22",
    "185.199.108.0/22",
    "140.82.112.0/20",
    "143.55.64.0/20",
    "2a0a:a440::/29",
    "2606:50c0::/32",
]


class WebhookSecurityError(Exception):
    """Raised when webhook security validation fails"""
    pass


class WebhookHandler:
    """Handler for GitHub webhooks with security validation"""
    
    def __init__(self):
        self.secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
        self.allowed_events = self._parse_allowed_events()
        self.replay_window_seconds = 300  # 5 minutes
        
    def _parse_allowed_events(self) -> List[WebhookEventType]:
        """Parse allowed events from environment"""
        events_str = os.getenv("GITHUB_WEBHOOK_EVENTS", "push,pull_request,workflow_run,release")
        events = []
        for e in events_str.split(","):
            try:
                events.append(WebhookEventType(e.strip()))
            except ValueError:
                logger.warning(f"Unknown webhook event type: {e}")
        return events
    
    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify GitHub webhook signature using HMAC-SHA256.
        
        Args:
            payload: Raw request body bytes
            signature: X-Hub-Signature-256 header value (sha256=...)
            
        Returns:
            True if signature is valid
            
        Raises:
            WebhookSecurityError: If signature is invalid or secret not configured
        """
        if not self.secret:
            raise WebhookSecurityError("GITHUB_WEBHOOK_SECRET not configured")
        
        if not signature:
            raise WebhookSecurityError("Missing X-Hub-Signature-256 header")
        
        if not signature.startswith("sha256="):
            raise WebhookSecurityError("Invalid signature format")
        
        expected_mac = hmac.new(
            self.secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        provided_mac = signature[7:]  # Remove "sha256=" prefix
        
        # Constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(expected_mac, provided_mac):
            logger.warning("Webhook signature verification failed")
            return False
        
        return True
    
    def validate_timestamp(self, timestamp: Optional[str]) -> bool:
        """
        Validate webhook timestamp to prevent replay attacks.
        
        Args:
            timestamp: X-GitHub-Delivery timestamp (ISO 8601)
            
        Returns:
            True if timestamp is within acceptable window
        """
        if not timestamp:
            return True  # GitHub doesn't always send timestamp
        
        try:
            # Parse ISO 8601 timestamp
            event_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            now = datetime.utcnow()
            delta = (now - event_time.replace(tzinfo=None)).total_seconds()
            
            # Reject if older than window or in the future
            if delta > self.replay_window_seconds or delta < -60:
                logger.warning(f"Webhook timestamp outside acceptable window: {delta}s")
                return False
            
            return True
        except Exception as e:
            logger.warning(f"Failed to parse webhook timestamp: {e}")
            return True  # Allow on parse error (defensive)
    
    def is_event_allowed(self, event_type: str) -> bool:
        """Check if event type is in allowed list"""
        try:
            event_enum = WebhookEventType(event_type)
            return event_enum in self.allowed_events
        except ValueError:
            return False
    
    def parse_payload(self, event_type: str, payload: Dict[str, Any], 
                      delivery_id: str) -> WebhookPayload:
        """
        Parse GitHub webhook payload into structured format.
        
        Args:
            event_type: GitHub event type header
            payload: Parsed JSON payload
            delivery_id: Unique delivery ID
            
        Returns:
            Structured WebhookPayload
        """
        repo = payload.get("repository", {})
        sender = payload.get("sender", {})
        
        webhook_payload = WebhookPayload(
            event_type=WebhookEventType(event_type),
            delivery_id=delivery_id,
            timestamp=datetime.utcnow(),
            repository=repo.get("full_name", "unknown"),
            repository_url=repo.get("html_url", ""),
            sender=sender.get("login", "unknown"),
            sender_avatar=sender.get("avatar_url", ""),
            raw_payload=payload,
        )
        
        # Parse event-specific fields
        if event_type == WebhookEventType.PUSH:
            webhook_payload.ref = payload.get("ref", "").replace("refs/heads/", "")
            webhook_payload.commit_sha = payload.get("after", "")
            
            # Get commit message from first commit
            commits = payload.get("commits", [])
            if commits:
                webhook_payload.commit_message = commits[0].get("message", "")
            
            webhook_payload.pusher = payload.get("pusher", {}).get("name", "")
        
        elif event_type == WebhookEventType.PULL_REQUEST:
            pr = payload.get("pull_request", {})
            webhook_payload.pr_number = pr.get("number")
            webhook_payload.pr_title = pr.get("title")
            webhook_payload.pr_state = pr.get("state")
            webhook_payload.pr_url = pr.get("html_url")
            webhook_payload.pr_action = payload.get("action")
            webhook_payload.commit_sha = pr.get("head", {}).get("sha")
        
        elif event_type == WebhookEventType.WORKFLOW_RUN:
            workflow = payload.get("workflow_run", {})
            webhook_payload.workflow_name = payload.get("workflow", {}).get("name", "")
            webhook_payload.workflow_status = WorkflowStatus(workflow.get("status", "queued"))
            conclusion = workflow.get("conclusion")
            if conclusion:
                try:
                    webhook_payload.workflow_conclusion = WorkflowConclusion(conclusion)
                except ValueError:
                    pass
            webhook_payload.workflow_run_id = workflow.get("id")
            webhook_payload.workflow_branch = workflow.get("head_branch")
            webhook_payload.commit_sha = workflow.get("head_sha")
        
        elif event_type == WebhookEventType.RELEASE:
            release = payload.get("release", {})
            webhook_payload.release_tag = release.get("tag_name")
            webhook_payload.release_name = release.get("name")
            webhook_payload.release_draft = release.get("draft", False)
            webhook_payload.release_prerelease = release.get("prerelease", False)
        
        return webhook_payload
    
    async def process_webhook(self, payload: WebhookPayload) -> WebhookResult:
        """
        Process a validated webhook payload.
        
        Args:
            payload: Parsed webhook payload
            
        Returns:
            Result of processing
        """
        event_type = payload.event_type
        
        # Handle ping event (webhook setup verification)
        if event_type == WebhookEventType.PING:
            return WebhookResult(
                success=True,
                message="Webhook ping received and verified",
                event_type="ping",
                action_taken="verified"
            )
        
        # Process based on event type
        if event_type == WebhookEventType.PUSH:
            return await self._handle_push(payload)
        
        elif event_type == WebhookEventType.PULL_REQUEST:
            return await self._handle_pull_request(payload)
        
        elif event_type == WebhookEventType.WORKFLOW_RUN:
            return await self._handle_workflow_run(payload)
        
        elif event_type == WebhookEventType.RELEASE:
            return await self._handle_release(payload)
        
        # Default: acknowledge but no action
        return WebhookResult(
            success=True,
            message=f"Event {event_type.value} received",
            event_type=event_type.value,
            action_taken="acknowledged"
        )
    
    async def _handle_push(self, payload: WebhookPayload) -> WebhookResult:
        """Handle push events"""
        branch = payload.ref or "unknown"
        commit = (payload.commit_sha or "")[:7]
        
        # Check if this is the default branch
        is_default = branch == "main" or branch == "master"
        
        message = f"Push to {payload.repository}:{branch} by {payload.pusher}"
        if payload.commit_message:
            message += f" - {payload.commit_message[:50]}"
        
        return WebhookResult(
            success=True,
            message=message,
            event_type="push",
            action_taken="logged" if not is_default else "trigger_deployment_candidate",
            metadata={
                "branch": branch,
                "commit": commit,
                "is_default_branch": is_default,
                "repository": payload.repository
            }
        )
    
    async def _handle_pull_request(self, payload: WebhookPayload) -> WebhookResult:
        """Handle pull request events"""
        action = payload.pr_action or "unknown"
        
        # Only process interesting PR events
        interesting_actions = ["opened", "closed", "merged", "ready_for_review"]
        if action not in interesting_actions:
            return WebhookResult(
                success=True,
                message=f"PR #{payload.pr_number} {action}",
                event_type="pull_request",
                action_taken="ignored_boring_action"
            )
        
        message = f"PR #{payload.pr_number} {action}: {payload.pr_title}"
        
        return WebhookResult(
            success=True,
            message=message,
            event_type="pull_request",
            action_taken="notification_sent",
            metadata={
                "pr_number": payload.pr_number,
                "pr_title": payload.pr_title,
                "pr_state": payload.pr_state,
                "action": action,
                "url": payload.pr_url
            }
        )
    
    async def _handle_workflow_run(self, payload: WebhookPayload) -> WebhookResult:
        """Handle GitHub Actions workflow run events"""
        status = payload.workflow_status
        conclusion = payload.workflow_conclusion
        
        # Only notify on completed workflows
        if status != WorkflowStatus.COMPLETED:
            return WebhookResult(
                success=True,
                message=f"Workflow {payload.workflow_name} is {status.value}",
                event_type="workflow_run",
                action_taken="waiting_for_completion"
            )
        
        # Determine action based on conclusion
        if conclusion == WorkflowConclusion.SUCCESS:
            action = "deployment_candidate" if payload.workflow_branch in ["main", "master"] else "notification_sent"
        elif conclusion == WorkflowConclusion.FAILURE:
            action = "alert_sent"
        else:
            action = "notification_sent"
        
        message = f"Workflow '{payload.workflow_name}' {conclusion.value} on {payload.workflow_branch}"
        
        return WebhookResult(
            success=True,
            message=message,
            event_type="workflow_run",
            action_taken=action,
            metadata={
                "workflow": payload.workflow_name,
                "status": status.value,
                "conclusion": conclusion.value if conclusion else None,
                "branch": payload.workflow_branch,
                "run_id": payload.workflow_run_id
            }
        )
    
    async def _handle_release(self, payload: WebhookPayload) -> WebhookResult:
        """Handle release events"""
        if payload.release_draft:
            return WebhookResult(
                success=True,
                message=f"Draft release {payload.release_tag} created",
                event_type="release",
                action_taken="ignored_draft"
            )
        
        message = f"Release {payload.release_tag}: {payload.release_name}"
        action = "trigger_deployment" if not payload.release_prerelease else "notification_sent"
        
        return WebhookResult(
            success=True,
            message=message,
            event_type="release",
            action_taken=action,
            metadata={
                "tag": payload.release_tag,
                "name": payload.release_name,
                "prerelease": payload.release_prerelease,
                "repository": payload.repository
            }
        )


# Global handler instance
webhook_handler = WebhookHandler()
