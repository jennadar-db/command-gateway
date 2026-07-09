"""Jira approval integration layer.

MVP behavior defaults to mock mode:
- create_child_approval_ticket returns a synthetic approval ticket id.
- validate_approval expects the local ApprovalStore record to be marked approved.

Replace the TODOs with real Jira REST calls when ready.
"""

from __future__ import annotations

import time
import uuid
from typing import Dict, Any

from gateway.config import settings
from gateway.core.types import ApprovalRecord
from gateway.core.approval_store import ApprovalStore


class JiraApprovalService:
    def __init__(self, store: ApprovalStore | None = None):
        self.store = store or ApprovalStore()

    def create_child_approval_ticket(self, approval_request_id: str, payload: Dict[str, Any], action_hash: str) -> str:
        if settings.approval_mode == "jira":
            # TODO: Implement real Jira child/subtask creation using settings.jira_base_url/token.
            # Return the created Jira issue key, e.g. "INC-1002-APPROVAL-1".
            raise NotImplementedError("Real Jira mode is not implemented yet. Use APPROVAL_MODE=mock.")

        parent = payload["ticket_id"]
        suffix = uuid.uuid4().hex[:6].upper()
        return f"{parent}-APPROVAL-{suffix}"

    def validate_approval(self, record: ApprovalRecord) -> tuple[bool, str]:
        if record.used:
            return False, "Approval request has already been used."

        if settings.approval_mode == "jira":
            # TODO: Query Jira issue status and ensure it is approved.
            raise NotImplementedError("Real Jira validation is not implemented yet. Use APPROVAL_MODE=mock.")

        latest = self.store.get(record.approval_request_id)
        if not latest:
            return False, "Approval request was not found in store."
        if latest.status != "approved":
            return False, f"Approval is not approved. Current status={latest.status}."
        return True, "Approval is valid."
