"""Simple file-backed approval store for local/MVP use.

For Cloud Run production, replace this with Firestore, Cloud SQL, Redis, or another
shared durable store. /tmp is not durable across instances.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from gateway.config import settings
from gateway.core.types import ApprovalRecord


class ApprovalStore:
    def __init__(self, path: str | None = None):
        self.path = Path(path or settings.approval_store_path)

    def _load(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text())
        except json.JSONDecodeError:
            return {}

    def _save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2, sort_keys=True))

    def put(self, record: ApprovalRecord) -> None:
        data = self._load()
        data[record.approval_request_id] = record.to_dict()
        self._save(data)

    def get(self, approval_request_id: str) -> Optional[ApprovalRecord]:
        data = self._load().get(approval_request_id)
        if not data:
            return None
        return ApprovalRecord(**data)

    def update_status(self, approval_request_id: str, status: str, used: bool | None = None) -> Optional[ApprovalRecord]:
        data = self._load()
        record = data.get(approval_request_id)
        if not record:
            return None
        record["status"] = status
        if used is not None:
            record["used"] = used
        data[approval_request_id] = record
        self._save(data)
        return ApprovalRecord(**record)
