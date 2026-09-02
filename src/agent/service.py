"""Native service-manager integration for the Sentinel agent.

Linux uses a real per-user systemd unit. Windows service installation is not
claimed until a Windows service dependency and an administrator-tested
installer are added; the CLI reports that limitation explicitly.
"""

from __future__ import annotations

import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
from typing import Sequence


class ServiceUnavailable(RuntimeError):
    """The requested native service manager is unavailable on this host."""


def unit_path() -> Path:
    if os.name == "nt":
        raise ServiceUnavailable("Windows service management is not implemented; run the agent with a Windows service wrapper")
    root = Path(os.getenv("XDG_CONFIG_HOME") or (Path.home() / ".config"))
    return root / "systemd" / "user" / "sentinel-agent.service"


def render_unit(config_path: Path) -> str:
    python = shlex.quote(sys.executable)
    config = shlex.quote(str(config_path))
    return f"""[Unit]
Description=Sentinel remote network sensor agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart={python} -m src.agent --config {config} start
Restart=on-failure
RestartSec=10
KillSignal=SIGTERM
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=default.target
"""


def _systemctl(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
    if shutil.which("systemctl") is None:
        raise ServiceUnavailable("systemctl is not installed; native service management is unavailable")
    return subprocess.run(
        ["systemctl", "--user", *args], text=True, capture_output=True, check=False
    )


def install(config_path: Path) -> str:
    target = unit_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_unit(config_path), encoding="utf-8")
    reload_result = _systemctl(("daemon-reload",))
    if reload_result.returncode:
        raise ServiceUnavailable(reload_result.stderr.strip() or "systemd user daemon-reload failed")
    enable_result = _systemctl(("enable", "sentinel-agent.service"))
    if enable_result.returncode:
        raise ServiceUnavailable(enable_result.stderr.strip() or "systemd user service enable failed")
    return str(target)


def uninstall() -> str:
    target = unit_path()
    _systemctl(("disable", "--now", "sentinel-agent.service"))
    target.unlink(missing_ok=True)
    _systemctl(("daemon-reload",))
    return str(target)


def command(action: str) -> str:
    if os.name == "nt":
        raise ServiceUnavailable(
            "Windows service management is not implemented; use an approved Windows service manager"
        )
    if action == "install":
        raise ValueError("service install requires the loaded agent configuration")
    if action == "uninstall":
        uninstall()
        return "service uninstalled"
    result = _systemctl((action, "sentinel-agent.service"))
    output = (result.stdout or result.stderr).strip()
    if result.returncode:
        raise ServiceUnavailable(output or f"systemd service {action} failed")
    return output or f"service {action} completed"
