"""High-level policy engine for Command Gateway decisions."""

from __future__ import annotations

import uuid
from typing import Any, Dict

from gateway.core.action_hash import generate_action_hash
from gateway.core.approval_store import ApprovalStore
from gateway.core.classifier import classify_command
from gateway.core.jira_approval import JiraApprovalService
from gateway.core.router import route_to_mcp
from gateway.core.types import ApprovalRecord, CommandRequest
from gateway.core.audit import audit_event


class PolicyEngine:
    def __init__(self):
        self.store = ApprovalStore()
        self.jira = JiraApprovalService(store=self.store)

    async def submit_operation(self, request: CommandRequest) -> Dict[str, Any]:
        classification = classify_command(request.technology, request.command)

        audit_event("command_classified", {
            "ticket_id": request.ticket_id,
            "technology": request.technology,
            "hostname": request.hostname,
            "command": request.command,
            "classification": classification.to_dict(),
        })

        if classification.category in {"BLOCKED", "UNKNOWN"}:
            return {
                "status": "blocked",
                "decision": "blocked_by_policy",
                "category": classification.category,
                "risk_level": classification.risk_level,
                "execution_performed": False,
                "reason": classification.reason,
                "matched_pattern": classification.matched_pattern,
            }

        if classification.category == "READ_ONLY":
            result = await route_to_mcp(request, classification)
            return {
                "status": "success" if result.get("status") not in {"failed", "error"} else "failed",
                "decision": "executed",
                "category": classification.category,
                "risk_level": classification.risk_level,
                "approval_required": False,
                "execution_performed": result.get("execution_performed", True),
                "selected_mcp_server": request.technology.lower(),
                "selected_mcp_tool": classification.selected_mcp_tool,
                "result": result,
            }

        if classification.category == "WRITE":
            return self._create_approval_request(request, classification)

        return {
            "status": "blocked",
            "decision": "blocked_by_policy",
            "category": "UNKNOWN",
            "execution_performed": False,
            "reason": "Unhandled command classification.",
        }

    def _create_approval_request(self, request: CommandRequest, classification) -> Dict[str, Any]:
        approval_request_id = f"apr-{uuid.uuid4().hex[:12]}"
        hash_payload = {
            "ticket_id": request.ticket_id,
            "technology": request.technology,
            "hostname": request.hostname,
            "command": request.command,
            "reason": request.reason,
            "selected_mcp_tool": classification.selected_mcp_tool,
            "category": classification.category,
        }
        action_hash = generate_action_hash(hash_payload)
        approval_ticket_id = self.jira.create_child_approval_ticket(
            approval_request_id=approval_request_id,
            payload=request.to_dict(),
            action_hash=action_hash,
        )

        record = ApprovalRecord(
            approval_request_id=approval_request_id,
            parent_ticket_id=request.ticket_id,
            approval_ticket_id=approval_ticket_id,
            technology=request.technology,
            hostname=request.hostname,
            command=request.command,
            reason=request.reason,
            selected_mcp_tool=classification.selected_mcp_tool or "linux_execute_command",
            category=classification.category,
            action_hash=action_hash,
            status="pending_approval",
            used=False,
        )
        self.store.put(record)

        audit_event("approval_created", record.to_dict())

        return {
            "status": "approval_required",
            "decision": "jira_child_ticket_created" if approval_ticket_id else "approval_required",
            "category": classification.category,
            "risk_level": classification.risk_level,
            "execution_performed": False,
            "approval_request_id": approval_request_id,
            "approval_ticket_id": approval_ticket_id,
            "message": "Human approval is required before executing this operation.",
        }

    async def check_approval_and_execute(self, approval_request_id: str) -> Dict[str, Any]:
        record = self.store.get(approval_request_id)
        if not record:
            return {
                "status": "blocked",
                "decision": "approval_not_found",
                "execution_performed": False,
                "reason": "Approval request id was not found.",
            }

        valid, reason = self.jira.validate_approval(record)
        if not valid:
            return {
                "status": "blocked",
                "decision": "approval_invalid",
                "approval_request_id": approval_request_id,
                "approval_ticket_id": record.approval_ticket_id,
                "execution_performed": False,
                "reason": reason,
            }

        request = CommandRequest(
            ticket_id=record.parent_ticket_id,
            technology=record.technology,
            hostname=record.hostname,
            command=record.command,
            reason=record.reason,
        )
        classification = classify_command(record.technology, record.command)

        # Defense-in-depth: reclassify before execution.
        if classification.category != "WRITE":
            return {
                "status": "blocked",
                "decision": "approval_reclassification_failed",
                "execution_performed": False,
                "reason": "Stored command no longer classifies as WRITE.",
            }

        result = await route_to_mcp(request, classification)
        self.store.update_status(approval_request_id, status="executed", used=True)

        audit_event("approved_command_executed", {
            "approval_request_id": approval_request_id,
            "approval_ticket_id": record.approval_ticket_id,
            "ticket_id": record.parent_ticket_id,
            "hostname": record.hostname,
            "command": record.command,
            "selected_mcp_tool": record.selected_mcp_tool,
            "result_status": result.get("status"),
        })

        return {
            "status": "success" if result.get("status") not in {"failed", "error"} else "failed",
            "decision": "approved_and_executed",
            "approval_request_id": approval_request_id,
            "approval_ticket_id": record.approval_ticket_id,
            "execution_performed": result.get("execution_performed", True),
            "selected_mcp_server": record.technology,
            "selected_mcp_tool": record.selected_mcp_tool,
            "result": result,
        }

    def approve_request_for_local_test(self, approval_request_id: str) -> Dict[str, Any]:
        updated = self.store.update_status(approval_request_id, status="approved")
        if not updated:
            return {"status": "failed", "reason": "Approval request id not found."}
        return {
            "status": "approved",
            "approval_request_id": approval_request_id,
            "approval_ticket_id": updated.approval_ticket_id,
            "message": "Local mock approval marked as approved.",
        }
