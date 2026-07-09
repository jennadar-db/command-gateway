"""Approval action hashing utilities."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict


def generate_action_hash(payload: Dict[str, Any]) -> str:
    """Generate a stable hash for the exact approved operation."""
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()