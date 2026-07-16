"""Runtime configuration for the Command Gateway MCP proxy."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # Downstream Linux MCP streamable HTTP endpoint, for example http://linux-mcp:9001/mcp.
    linux_mcp_url: str = os.getenv("LINUX_MCP_URL", "")

    # Approval/Jira settings. MVP defaults to mock mode.
    approval_mode: str = os.getenv("APPROVAL_MODE", "mock")  # mock | jira
    jira_base_url: str = os.getenv("JIRA_BASE_URL", "")
    jira_project_key: str = os.getenv("JIRA_PROJECT_KEY", "")
    jira_issue_type: str = os.getenv("JIRA_APPROVAL_ISSUE_TYPE", "Task")
    jira_bearer_token: str = os.getenv("JIRA_BEARER_TOKEN", "")

    # Local state store for pending approvals. For Cloud Run/prod replace with Firestore/DB.
    approval_store_path: str = os.getenv("APPROVAL_STORE_PATH", "/tmp/command_gateway_approvals.json")

    # Guardrails
    unknown_command_default_decision: str = os.getenv("UNKNOWN_COMMAND_DEFAULT_DECISION", "block")
    max_stdout_chars: int = int(os.getenv("MAX_STDOUT_CHARS", "8000"))
    max_stderr_chars: int = int(os.getenv("MAX_STDERR_CHARS", "4000"))


settings = Settings()
