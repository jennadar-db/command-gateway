"""Structured audit logging."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict

logger = logging.getLogger("command_gateway.audit")


def audit_event(event_type: str, payload: Dict[str, Any]) -> str:
    audit_id = f"audit-{uuid.uuid4().hex[:12]}"
    event = {
        "audit_id": audit_id,
        "event_type": event_type,
        **payload,
    }
    logger.info(json.dumps(event, sort_keys=True, default=str))
    return audit_id
