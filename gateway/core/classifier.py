"""Command classifier and downstream MCP tool selector.

This module intentionally uses deterministic regex rules. Do not rely only on an LLM
for allow/block decisions when executing commands.
"""

from __future__ import annotations

import re
from typing import Iterable

from gateway.core.types import Classification


# Blocked commands are evaluated first. Keep this list conservative.
BLOCKED_PATTERNS: list[tuple[str, str]] = [
    (r"rm\s+-rf\s+/", "Destructive recursive delete from root"),
    (r"rm\s+-rf\s+/\*", "Destructive recursive delete from root wildcard"),
    (r"rm\s+-rf\s+/(etc|var|usr|home|boot)(\s|$)", "Destructive delete of critical system directory"),
    (r"find\s+/.*-delete", "Mass deletion using find"),
    (r"find\s+/.*-exec\s+rm", "Mass deletion using find -exec rm"),
    (r"\bmkfs(\.|\s|$)", "Filesystem formatting"),
    (r"\bmkswap\b", "Swap formatting"),
    (r"\bfdisk\b|\bparted\b|\bsfdisk\b", "Partition table modification"),
    (r"\bdd\s+if=", "Raw disk copying/write risk"),
    (r"\bdd\s+.*of=/dev/", "Raw write to block device"),
    (r"\bwipefs\b|\bblkdiscard\b", "Filesystem/device wipe"),
    (r"/etc/shadow|/etc/gshadow", "Credential database access"),
    (r"/root/\.ssh/id_rsa|\.ssh/id_rsa", "Private SSH key access"),
    (r"/etc/krb5\.keytab", "Kerberos keytab access"),
    (r"/var/lib/sss/secrets", "SSSD secret access"),
    (r"curl.*\|\s*(bash|sh)", "Remote download piped to shell"),
    (r"wget.*\|\s*(bash|sh)", "Remote download piped to shell"),
    (r"bash\s+<\(|sh\s+<\(", "Process substitution executing remote/local script"),
    (r"\bnc\s+.*-e\b|\bncat\s+.*-e\b", "Netcat reverse shell pattern"),
    (r"bash\s+-i", "Interactive shell pattern"),
    (r"/dev/tcp/", "Shell TCP redirection pattern"),
    (r"\b(reboot|shutdown|halt|poweroff)\b", "Host reboot/shutdown command"),
    (r"systemctl\s+(stop|disable)\s+auditd", "Audit service tampering"),
    (r"history\s+-c", "Shell history deletion"),
    (r"truncate\s+-s\s+0\s+/var/log/", "Log tampering"),
    (r"rm\s+/var/log/", "Log deletion"),
    # Shell control/meta characters. Conservative for MVP.
    (r";", "Shell command chaining is blocked"),
    (r"&&", "Shell command chaining is blocked"),
    (r"\|\|", "Shell conditional chaining is blocked"),
    (r"`", "Shell backtick expansion is blocked"),
    (r"\$\(", "Shell command substitution is blocked"),
    (r">|<", "Shell redirection is blocked"),
    (r"[\n\r]", "Multiline command is blocked"),
]

READ_ONLY_PATTERNS: list[tuple[str, str]] = [
    (r"^date$", "linux_execute_command"),
    (r"^hostname$", "hostname_check"),
    (r"^uptime$", "uptime_check"),
    (r"^whoami$", "linux_execute_command"),
    (r"^id$", "linux_execute_command"),
    (r"^df\s+-h$", "disk_check"),
    (r"^free\s+-(m|h)$", "memory_check"),
    (r"^ps\s+aux$", "process_check"),
    (r"^systemctl\s+status\s+[a-zA-Z0-9_.@-]+(\s+--no-pager)?$", "service_status"),
    (r"^journalctl\s+-u\s+[a-zA-Z0-9_.@-]+(\s+--no-pager)?(\s+-n\s+[0-9]+)?$", "journal_read"),
    (r"^tail\s+-n\s+[0-9]+\s+/var/log/[a-zA-Z0-9_./-]+$", "log_tail"),
    (r"^ss\s+-tulpen$", "port_check"),
    (r"^netstat\s+-tulpen$", "port_check"),
    (r"^dig\s+[a-zA-Z0-9_.-]+$", "dns_check"),
    (r"^nslookup\s+[a-zA-Z0-9_.-]+$", "dns_check"),
    (r"^ping\s+-c\s+[0-9]+\s+[a-zA-Z0-9_.-]+$", "network_check"),
    # ad_check is assumed read-only for MVP. Allow common script-path variants.
    (r"^(?:[a-zA-Z0-9_./-]+/)?ad_check(?:\.sh)?(\s+--[a-zA-Z0-9_-]+(?:[=\s][a-zA-Z0-9_./:@\\=-]+)?)*$", "ad_check"),
]

WRITE_PATTERNS: list[tuple[str, str, str]] = [
    (r"^systemctl\s+restart\s+[a-zA-Z0-9_.@-]+$", "service_restart", "medium"),
    (r"^systemctl\s+reload\s+[a-zA-Z0-9_.@-]+$", "service_reload", "medium"),
    (r"^service\s+[a-zA-Z0-9_.@-]+\s+restart$", "service_restart", "medium"),
    (r"^service\s+[a-zA-Z0-9_.@-]+\s+reload$", "service_reload", "medium"),
    (r"^kill\s+-?[0-9]+\s+[0-9]+$", "process_kill", "high"),
    (r"^pkill\s+[a-zA-Z0-9_.@-]+$", "process_kill", "high"),
]


def _match(patterns: Iterable, command: str):
    for item in patterns:
        pattern = item[0]
        if re.search(pattern, command, flags=re.IGNORECASE):
            return item
    return None


def classify_linux_command(command: str) -> Classification:
    normalized = " ".join(command.strip().split())

    blocked = _match(BLOCKED_PATTERNS, normalized)
    if blocked:
        pattern, reason = blocked
        return Classification(
            category="BLOCKED",
            decision="block",
            reason=reason,
            selected_mcp_tool=None,
            matched_pattern=pattern,
            risk_level="critical",
        )

    for pattern, tool in READ_ONLY_PATTERNS:
        if re.match(pattern, normalized, flags=re.IGNORECASE):
            return Classification(
                category="READ_ONLY",
                decision="execute",
                reason="Read-only Linux command allowed by policy",
                selected_mcp_tool=tool,
                matched_pattern=pattern,
                risk_level="low",
            )

    for pattern, tool, risk in WRITE_PATTERNS:
        if re.match(pattern, normalized, flags=re.IGNORECASE):
            return Classification(
                category="WRITE",
                decision="require_approval",
                reason="Linux write command requires human approval",
                selected_mcp_tool=tool,
                matched_pattern=pattern,
                risk_level=risk,
            )

    return Classification(
        category="UNKNOWN",
        decision="block",
        reason="Unknown Linux command blocked by default",
        selected_mcp_tool=None,
        matched_pattern=None,
        risk_level="high",
    )


def classify_command(technology: str, command: str) -> Classification:
    if technology.lower() == "linux":
        return classify_linux_command(command)
    return Classification(
        category="UNKNOWN",
        decision="block",
        reason=f"Unsupported technology: {technology}",
        selected_mcp_tool=None,
        risk_level="high",
    )
