"""Installed command-line entry point for a Sentinel remote sensor."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Sequence

from src.agent import __version__
from src.agent.config import AgentConfig, default_config_path


def _config_path(args: argparse.Namespace) -> Path:
    return Path(args.config).expanduser() if args.config else default_config_path()


def _load(args: argparse.Namespace, *, identity: bool = False) -> AgentConfig:
    config = AgentConfig.load(_config_path(args))
    config.validate(require_identity=identity)
    return config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sentinel-agent", description="Sentinel remote network sensor agent"
    )
    parser.add_argument("--version", action="version", version=f"sentinel-agent {__version__}")
    parser.add_argument("--config", help="agent configuration path")
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="create an agent configuration")
    init.add_argument("--server-url", required=True)
    init.add_argument("--interface", required=True)
    init.add_argument("--buffer-dir")
    init.add_argument("--environment", choices=("development", "production"), default="development")
    init.add_argument("--capture-filter")
    init.add_argument("--batch-size", type=int, default=6)
    init.add_argument("--batch-interval", type=float, default=5.0)
    init.add_argument("--max-buffer-batches", type=int, default=256)
    init.add_argument("--max-buffer-bytes", type=int, default=64 * 1024 * 1024)
    init.add_argument("--heartbeat-interval", type=int, default=20)
    init.add_argument("--retry-base", type=float, default=1.0)
    init.add_argument("--retry-max", type=float, default=60.0)
    init.add_argument("--retry-jitter", type=float, default=0.0)
    init.add_argument("--overflow-policy", choices=("DROP_OLDEST", "REJECT_NEW"), default="DROP_OLDEST")
    init.add_argument("--log-level", choices=("DEBUG", "INFO", "WARNING", "ERROR"), default="INFO")
    init.add_argument("--tls-ca", help="custom CA bundle for the central HTTPS certificate")
    init.add_argument("--tls-client-cert", help="optional client certificate for future mTLS deployments")
    init.add_argument("--tls-client-key", help="optional client private key for future mTLS deployments")
    init.add_argument(
        "--tls-insecure",
        action="store_true",
        help="disable TLS verification for explicitly configured development testing only",
    )

    register = commands.add_parser("register", help="consume a one-time enrollment credential")
    register.add_argument("--enrollment-token", required=True)
    commands.add_parser("start", help="start packet collection and remote telemetry")
    commands.add_parser("stop", help="request graceful shutdown of the local agent process")
    commands.add_parser("restart", help="restart the foreground agent process")
    commands.add_parser("status", help="show local and central sensor health")

    config = commands.add_parser("config", help="show or validate configuration")
    config.add_subparsers(dest="config_action").add_parser("validate", help="validate without capture or network access")
    commands.add_parser("diagnostics", help="show operator-safe platform and connectivity diagnostics")

    service = commands.add_parser("service", help="manage the native service manager")
    service.add_argument("action", choices=("install", "uninstall", "start", "stop", "restart", "status"))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        path = _config_path(args)
        if args.command == "init":
            config = AgentConfig(
                server_url=args.server_url,
                interface=args.interface,
                environment=args.environment,
                capture_filter=args.capture_filter,
                batch_size=args.batch_size,
                batch_interval_seconds=args.batch_interval,
                max_buffer_batches=args.max_buffer_batches,
                max_buffer_bytes=args.max_buffer_bytes,
                heartbeat_interval_seconds=args.heartbeat_interval,
                retry_base_seconds=args.retry_base,
                retry_max_seconds=args.retry_max,
                retry_jitter_seconds=args.retry_jitter,
                buffer_overflow_policy=args.overflow_policy,
                log_level=args.log_level,
                tls_ca_path=Path(args.tls_ca).expanduser() if args.tls_ca else None,
                tls_client_cert_path=Path(args.tls_client_cert).expanduser() if args.tls_client_cert else None,
                tls_client_key_path=Path(args.tls_client_key).expanduser() if args.tls_client_key else None,
                tls_verify=not args.tls_insecure,
            )
            config.validate()
            if args.buffer_dir:
                config.buffer_dir = Path(args.buffer_dir).expanduser()
            print(config.save(path))
            return 0

        if args.command == "config":
            config = _load(args)
            if args.config_action == "validate":
                from src.agent.diagnostics import validate_config

                print(json.dumps(validate_config(config), indent=2, default=str))
            else:
                print(json.dumps(config.redacted(), indent=2, default=str))
            return 0

        if args.command == "diagnostics":
            from src.agent.diagnostics import collect

            print(json.dumps(collect(_load(args)), indent=2, default=str))
            return 0

        if args.command == "service":
            from src.agent.service import command, install

            if args.action == "install":
                _load(args)
                print(install(path))
            else:
                print(command(args.action))
            return 0

        from src.agent.client import SensorAgent, SensorClient, stop_pid

        if args.command == "register":
            config = _load(args)
            response = SensorClient(config).register(args.enrollment_token)
            config.sensor_id = response["sensor_id"]
            config.runtime_token = response["runtime_token"]
            config.validate(require_identity=True)
            config.save(path)
            print(json.dumps({"sensor_id": config.sensor_id, "registered": True}, indent=2))
            return 0
        if args.command == "status":
            config = _load(args)
            agent = SensorAgent(config) if config.sensor_id and config.runtime_token else None
            result = agent.local_status() if agent else {"config": config.redacted(), "buffered_batches": 0}
            if agent:
                try:
                    result["central"] = SensorClient(config).status()
                except Exception as exc:
                    result["central_error"] = str(exc)
            print(json.dumps(result, indent=2, default=str))
            return 0
        if args.command == "stop":
            print("stopped" if stop_pid(_load(args).pid_path) else "agent is not running")
            return 0

        config = _load(args, identity=True)
        if args.command == "restart":
            stop_pid(config.pid_path)
            time.sleep(0.25)
        if args.command in {"start", "restart"}:
            SensorAgent(config).run()
            return 0
        return 2
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
