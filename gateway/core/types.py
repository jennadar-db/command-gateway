"""Shared data structures for the Command Gateway."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional


@dataclass
class CommandRequest:
    ticket_id: str
    technology: str
    hostname: str
    command: str
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Classification:
    category: str               # READ_ONLY | WRITE | BLOCKED | UNKNOWN
    decision: str               # execute | require_approval | block
    reason: str
    selected_mcp_tool: Optional[str] = None
    matched_pattern: Optional[str] = None
    risk_level: str = "low"     # low | medium | high | critical

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ApprovalRecord:
    approval_request_id: str
    parent_ticket_id: str
    approval_ticket_id: str
    technology: str
    hostname: str
    command: str
    reason: str
    selected_mcp_tool: str
    category: str
    action_hash: str
    status: str                 # pending_approval | approved | rejected | executed
    used: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
