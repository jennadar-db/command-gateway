from __future__ import annotations

import re
import subprocess
import time
from typing import Any, Dict

from mcp.server.fastmcp import FastMCP


mcp = FastMCP("linux-mcp", host="0.0.0.0", port=9001)


SAFE_EXACT_COMMANDS = {
    "date",
    "hostname",
    "uptime",
    "whoami",
    "id",
    "df -h",
    "free -m",
    "free -h",
    "ps aux",
    "ss -tulpen",
    "netstat -tulpen",
}

TOOL_PATTERNS = {
    "linux_execute_command": [
        r"^date$",
        r"^whoami$",
        r"^id$",
    ],
    "hostname_check": [r"^hostname$"],
    "uptime_check": [r"^uptime$"],
    "disk_check": [r"^df\s+-h$"],
    "memory_check": [r"^free\s+-(m|h)$"],
    "process_check": [r"^ps\s+aux$"],
    "service_status": [r"^systemctl\s+status\s+[a-zA-Z0-9_.@-]+(\s+--no-pager)?$"],
    "journal_read": [r"^journalctl\s+-u\s+[a-zA-Z0-9_.@-]+(\s+--no-pager)?(\s+-n\s+[0-9]+)?$"],
    "log_tail": [r"^tail\s+-n\s+[0-9]+\s+/var/log/[a-zA-Z0-9_./-]+$"],
    "port_check": [r"^(ss|netstat)\s+-tulpen$"],
    "dns_check": [r"^(dig|nslookup)\s+[a-zA-Z0-9_.-]+$"],
    "network_check": [r"^ping\s+-c\s+[0-9]+\s+[a-zA-Z0-9_.-]+$"],
    "ad_check": [r"^(?:[a-zA-Z0-9_./-]+/)?ad_check(?:\.sh)?(\s+--[a-zA-Z0-9_-]+(?:[=\s][a-zA-Z0-9_./:@\\=-]+)?)*$"],
    "service_restart": [r"^systemctl\s+restart\s+[a-zA-Z0-9_.@-]+$", r"^service\s+[a-zA-Z0-9_.@-]+\s+restart$"],
    "service_reload": [r"^systemctl\s+reload\s+[a-zA-Z0-9_.@-]+$", r"^service\s+[a-zA-Z0-9_.@-]+\s+reload$"],
    "process_kill": [r"^kill\s+-?[0-9]+\s+[0-9]+$", r"^pkill\s+[a-zA-Z0-9_.@-]+$"],
}

BLOCKED_META_PATTERNS = [r";", r"&&", r"\|\|", r"`", r"\$\(", r">|<", r"[\n\r]"]


def is_ad_check(command: str) -> bool:
    normalized = " ".join(command.strip().split())
    if not normalized:
        return False

    first_token = normalized.split(" ", 1)[0]
    basename = first_token.rsplit("/", 1)[-1]
    return basename in {"ad_check", "ad_check.sh"}


def _normalize(command: str) -> str:
    return " ".join(command.strip().split())


def _validate(tool_name: str, command: str) -> str:
    normalized = _normalize(command)

    for blocked in BLOCKED_META_PATTERNS:
        if re.search(blocked, normalized):
            raise ValueError(f"Command is blocked by meta-character policy: {normalized}")

    allowed_patterns = TOOL_PATTERNS.get(tool_name)
    if not allowed_patterns:
        raise ValueError(f"Unsupported MCP tool requested: {tool_name}")

    if not any(re.match(pattern, normalized, flags=re.IGNORECASE) for pattern in allowed_patterns):
        raise ValueError(
            f"Command does not match tool policy. tool={tool_name} command={normalized}"
        )

    return normalized


def run_safe_command(command: str) -> Dict[str, Any]:
    normalized = _normalize(command)

    args = normalized.split(" ")

    started = time.time()

    completed = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=15,
        shell=False,
    )

    duration_ms = int((time.time() - started) * 1000)

    return {
        "status": "success" if completed.returncode == 0 else "failed",
        "execution_performed": True,
        "exit_code": completed.returncode,
        "stdout": completed.stdout[-8000:],
        "stderr": completed.stderr[-4000:],
        "duration_ms": duration_ms,
    }


def _execute(
    *,
    tool_name: str,
    hostname: str,
    command: str,
    ticket_id: str = "",
    reason: str = "",
) -> Dict[str, Any]:
    normalized = _validate(tool_name, command)

    print(
        {
            "event": "linux_mcp_execute_request",
            "hostname": hostname,
            "tool": tool_name,
            "command": normalized,
            "ticket_id": ticket_id,
            "reason": reason,
        }
    )

    # Demo behavior for ad_check. Replace with real execution later.
    if is_ad_check(normalized):
        return {
            "status": "success",
            "execution_performed": True,
            "exit_code": 0,
            "stdout": (
                "MOCK ad_check result: AD connectivity looks reachable. "
                "LDAP bind test simulated successfully. DNS SRV lookup simulated successfully."
            ),
            "stderr": "",
            "duration_ms": 10,
            "tool": tool_name,
        }

    if normalized not in SAFE_EXACT_COMMANDS:
        return {
            "status": "blocked",
            "execution_performed": False,
            "reason": f"Command is not allowlisted by linux-mcp demo executor: {normalized}",
            "tool": tool_name,
        }

    result = run_safe_command(normalized)
    result["tool"] = tool_name
    return result


@mcp.tool()
def linux_execute_command(hostname: str, command: str, ticket_id: str = "", reason: str = "") -> Dict[str, Any]:
    return _execute(
        tool_name="linux_execute_command",
        hostname=hostname,
        command=command,
        ticket_id=ticket_id,
        reason=reason,
    )


@mcp.tool()
def hostname_check(hostname: str, command: str, ticket_id: str = "", reason: str = "") -> Dict[str, Any]:
    return _execute(tool_name="hostname_check", hostname=hostname, command=command, ticket_id=ticket_id, reason=reason)


@mcp.tool()
def uptime_check(hostname: str, command: str, ticket_id: str = "", reason: str = "") -> Dict[str, Any]:
    return _execute(tool_name="uptime_check", hostname=hostname, command=command, ticket_id=ticket_id, reason=reason)


@mcp.tool()
def disk_check(hostname: str, command: str, ticket_id: str = "", reason: str = "") -> Dict[str, Any]:
    return _execute(tool_name="disk_check", hostname=hostname, command=command, ticket_id=ticket_id, reason=reason)


@mcp.tool()
def memory_check(hostname: str, command: str, ticket_id: str = "", reason: str = "") -> Dict[str, Any]:
    return _execute(tool_name="memory_check", hostname=hostname, command=command, ticket_id=ticket_id, reason=reason)


@mcp.tool()
def process_check(hostname: str, command: str, ticket_id: str = "", reason: str = "") -> Dict[str, Any]:
    return _execute(tool_name="process_check", hostname=hostname, command=command, ticket_id=ticket_id, reason=reason)


@mcp.tool()
def service_status(hostname: str, command: str, ticket_id: str = "", reason: str = "") -> Dict[str, Any]:
    return _execute(tool_name="service_status", hostname=hostname, command=command, ticket_id=ticket_id, reason=reason)


@mcp.tool()
def journal_read(hostname: str, command: str, ticket_id: str = "", reason: str = "") -> Dict[str, Any]:
    return _execute(tool_name="journal_read", hostname=hostname, command=command, ticket_id=ticket_id, reason=reason)


@mcp.tool()
def log_tail(hostname: str, command: str, ticket_id: str = "", reason: str = "") -> Dict[str, Any]:
    return _execute(tool_name="log_tail", hostname=hostname, command=command, ticket_id=ticket_id, reason=reason)


@mcp.tool()
def port_check(hostname: str, command: str, ticket_id: str = "", reason: str = "") -> Dict[str, Any]:
    return _execute(tool_name="port_check", hostname=hostname, command=command, ticket_id=ticket_id, reason=reason)


@mcp.tool()
def dns_check(hostname: str, command: str, ticket_id: str = "", reason: str = "") -> Dict[str, Any]:
    return _execute(tool_name="dns_check", hostname=hostname, command=command, ticket_id=ticket_id, reason=reason)


@mcp.tool()
def network_check(hostname: str, command: str, ticket_id: str = "", reason: str = "") -> Dict[str, Any]:
    return _execute(tool_name="network_check", hostname=hostname, command=command, ticket_id=ticket_id, reason=reason)


@mcp.tool()
def ad_check(hostname: str, command: str, ticket_id: str = "", reason: str = "") -> Dict[str, Any]:
    return _execute(tool_name="ad_check", hostname=hostname, command=command, ticket_id=ticket_id, reason=reason)


@mcp.tool()
def service_restart(hostname: str, command: str, ticket_id: str = "", reason: str = "") -> Dict[str, Any]:
    return _execute(tool_name="service_restart", hostname=hostname, command=command, ticket_id=ticket_id, reason=reason)


@mcp.tool()
def service_reload(hostname: str, command: str, ticket_id: str = "", reason: str = "") -> Dict[str, Any]:
    return _execute(tool_name="service_reload", hostname=hostname, command=command, ticket_id=ticket_id, reason=reason)


@mcp.tool()
def process_kill(hostname: str, command: str, ticket_id: str = "", reason: str = "") -> Dict[str, Any]:
    return _execute(tool_name="process_kill", hostname=hostname, command=command, ticket_id=ticket_id, reason=reason)


@mcp.tool()
def get_linux_mcp_status() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "linux-mcp",
        "transport": "streamable-http",
        "allowlisted_exact_commands": sorted(SAFE_EXACT_COMMANDS),
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")