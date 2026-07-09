from __future__ import annotations

import shlex
import subprocess
import time
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


app = FastAPI(title="Linux MCP Demo Executor", version="0.1.0")


class ExecuteRequest(BaseModel):
    hostname: str
    command: str
    tool: Optional[str] = None
    ticket_id: Optional[str] = None
    reason: Optional[str] = None


SAFE_EXACT_COMMANDS = {
    "date": ["date"],
    "hostname": ["hostname"],
    "uptime": ["uptime"],
    "whoami": ["whoami"],
    "id": ["id"],
    "df -h": ["df", "-h"],
    "free -m": ["free", "-m"],
    "free -h": ["free", "-h"],
}


def is_ad_check(command: str) -> bool:
    return command.strip().startswith("ad_check")


def run_safe_command(command: str) -> Dict[str, Any]:
    normalized = " ".join(command.strip().split())

    if normalized not in SAFE_EXACT_COMMANDS:
        raise HTTPException(
            status_code=403,
            detail=f"Command is not allowed by linux-mcp demo executor: {normalized}",
        )

    args = SAFE_EXACT_COMMANDS[normalized]

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


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "linux-mcp-demo",
    }


@app.post("/execute")
def execute(request: ExecuteRequest):
    print(
        {
            "event": "linux_mcp_execute_request",
            "hostname": request.hostname,
            "tool": request.tool,
            "command": request.command,
            "ticket_id": request.ticket_id,
            "reason": request.reason,
        }
    )

    # Demo behavior for ad_check.
    # Replace this with real ad_check execution on secgcpagent01 later.
    if is_ad_check(request.command):
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
            "tool": request.tool or "ad_check",
        }

    return run_safe_command(request.command)