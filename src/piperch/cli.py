from __future__ import annotations

import argparse
import logging
import os
import socket
import sys
import threading
import webbrowser
from contextlib import ExitStack
from copy import deepcopy
from dataclasses import dataclass, field
from ipaddress import AddressValueError, IPv4Address
from pathlib import Path
from typing import TYPE_CHECKING, Literal, NoReturn, Protocol
from uuid import uuid4

import uvicorn
from uvicorn.config import LOGGING_CONFIG

from piperch.app import create_app
from piperch.application.control import AppControl
from piperch.database import run_migrations
from piperch.paths import AppPaths

_GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS = 5
_LOOPBACK_HOST = "127.0.0.1"
_PIPERCH_LOGGING_CONFIG = deepcopy(LOGGING_CONFIG)
_PIPERCH_LOGGING_CONFIG["loggers"]["piperch"] = {
    "handlers": ["default"],
    "level": "INFO",
    "propagate": False,
}

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from typing import Any


@dataclass(slots=True)
class Args:
    """声明并校验命令行参数，向程序提供类型明确的配置。"""

    command: Literal["serve", "db"]
    data_dir: Path | None = None
    port: int = 9303
    hosts: list[str] = field(default_factory=list[str])
    verbose: bool = False
    action: Literal["upgrade"] | None = None

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        commands = parser.add_subparsers(dest="command", required=True)

        serve = commands.add_parser("serve", help="迁移数据库并启动本地服务", argument_default=argparse.SUPPRESS)
        serve.add_argument("--port")
        serve.add_argument(
            "--host",
            dest="hosts",
            action="append",
            metavar="IP",
            help="追加监听的本机 IPv4 地址，可重复传入，始终监听 127.0.0.1",
        )
        serve.add_argument("--data-dir")
        serve.add_argument("--verbose", action="store_true", help="输出每个 HTTP 请求的访问日志")

        database = commands.add_parser("db", help="数据库管理", argument_default=argparse.SUPPRESS)
        database.add_argument("action", choices=["upgrade"])
        database.add_argument("--data-dir")

    @classmethod
    def from_ns(cls, namespace: argparse.Namespace) -> Args:
        return cls(**vars(namespace))

    def __post_init__(self) -> None:
        if self.data_dir is not None:
            self.data_dir = Path(self.data_dir)

        try:
            self.port = int(self.port)
        except ValueError as error:
            raise ValueError("端口必须是整数。") from error
        if not 1 <= self.port <= 65535:
            raise ValueError("端口必须位于 1 到 65535 之间。")

        hosts: list[str] = []
        for value in self.hosts:
            try:
                address = IPv4Address(value)
            except AddressValueError as error:
                raise ValueError("监听地址必须是有效的 IPv4 地址。") from error
            if address.is_unspecified:
                raise ValueError("请指定具体的 IPv4 地址，不能使用 0.0.0.0。")
            hosts.append(str(address))
        self.hosts = hosts

    @classmethod
    def parse(cls) -> Args:
        parser = argparse.ArgumentParser(prog="piperch", description="PiPerch 本地 Pixiv 管理器")
        cls.add_arguments(parser)
        namespace = parser.parse_args()
        try:
            return cls.from_ns(namespace)
        except ValueError as error:
            parser.error(str(error))


class _NonSuccessAccessFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not isinstance(record.args, tuple) or len(record.args) < 5:
            return True
        status_code = record.args[4]
        return not isinstance(status_code, int) or not 200 <= status_code < 300


def _logging_config(*, verbose: bool) -> dict[str, Any]:
    config = deepcopy(_PIPERCH_LOGGING_CONFIG)
    if verbose:
        return config
    config.setdefault("filters", {})["non_success_access"] = {"()": _NonSuccessAccessFilter}
    config["handlers"]["access"]["filters"] = ["non_success_access"]
    return config


class _ServerControl(Protocol):
    should_exit: bool
    force_exit: bool


class _ServerLifecycle:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._server: _ServerControl | None = None
        self._restart_requested = False
        self._manual_shutdown = False

    def bind(self, server: _ServerControl) -> None:
        with self._lock:
            self._server = server
            if self._restart_requested or self._manual_shutdown:
                server.should_exit = True

    def request_restart(self) -> None:
        with self._lock:
            self._restart_requested = True
            if self._server is not None:
                self._server.should_exit = True

    def take_restart_request(self) -> bool:
        with self._lock:
            restart = self._restart_requested and not self._manual_shutdown
            self._restart_requested = False
            self._manual_shutdown = False
            self._server = None
            return restart

    @property
    def should_exit(self) -> bool:
        with self._lock:
            return bool(self._server and self._server.should_exit)

    @should_exit.setter
    def should_exit(self, value: bool) -> None:
        with self._lock:
            self._manual_shutdown = self._manual_shutdown or value
            if self._server is not None:
                self._server.should_exit = value

    @property
    def force_exit(self) -> bool:
        with self._lock:
            return bool(self._server and self._server.force_exit)

    @force_exit.setter
    def force_exit(self, value: bool) -> None:
        with self._lock:
            self._manual_shutdown = self._manual_shutdown or value
            if self._server is not None:
                self._server.force_exit = value


def watch_terminal_interrupts(read_character: Callable[[], str], server: _ServerControl) -> None:
    """兼容把 Ctrl-C 作为 ETX 字符传入 stdin 的 Windows 伪终端。"""
    interrupt_count = 0
    while not server.force_exit:
        character = read_character()
        if not character:
            return
        if character != "\x03":
            continue
        interrupt_count += 1
        if interrupt_count > 1:
            server.force_exit = True
        else:
            server.should_exit = True


def _start_terminal_interrupt_watcher(server: _ServerLifecycle) -> None:
    if os.name != "nt" or not sys.stdin.isatty():
        return
    import msvcrt

    threading.Thread(
        target=watch_terminal_interrupts,
        args=(msvcrt.getwch, server),
        name="piperch-terminal-interrupt",
        daemon=True,
    ).start()


def _bind_sockets(hosts: Sequence[str], port: int) -> list[socket.socket]:
    sockets: list[socket.socket] = []
    with ExitStack() as cleanup:
        for host in hosts:
            listener = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
            cleanup.callback(listener.close)
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((host, port))
            sockets.append(listener)
        cleanup.pop_all()
    return sockets


def run_server(
    paths: AppPaths,
    port: int,
    *,
    additional_hosts: Sequence[str] = (),
    open_browser: bool = False,
    verbose: bool = False,
) -> None:
    lifecycle = _ServerLifecycle()
    hosts = tuple(dict.fromkeys((_LOOPBACK_HOST, *additional_hosts)))
    watcher_started = False
    while True:
        control = AppControl(
            instance_id=str(uuid4()),
            request_restart=lifecycle.request_restart,
            is_stopping=lambda: lifecycle.should_exit,
        )
        config = uvicorn.Config(
            create_app(paths, control),
            host=_LOOPBACK_HOST,
            port=port,
            workers=1,
            timeout_graceful_shutdown=_GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS,
            log_config=_logging_config(verbose=verbose),
            access_log=True,
        )
        server = uvicorn.Server(config)
        try:
            sockets = _bind_sockets(hosts, port) if len(hosts) > 1 else []
        except OSError as error:
            logging.getLogger("uvicorn.error").error(error)
            raise SystemExit(3) from None
        if sockets:
            logger = logging.getLogger("uvicorn.error")
            for host in hosts:
                logger.info("Uvicorn running on http://%s:%d (Press CTRL+C to quit)", host, port)
        if open_browser:
            threading.Timer(
                1,
                webbrowser.open,
                args=(f"http://{_LOOPBACK_HOST}:{config.port}",),
            ).start()
        open_browser = False
        lifecycle.bind(server)
        if not watcher_started:
            _start_terminal_interrupt_watcher(lifecycle)
            watcher_started = True
        try:
            if sockets:
                server.run(sockets=sockets)
            else:
                server.run()
        finally:
            for listener in sockets:
                listener.close()
        if not server.started:
            raise SystemExit(3)
        if not lifecycle.take_restart_request():
            return


def main() -> NoReturn:
    arguments = Args.parse()
    paths = AppPaths.from_data_dir(arguments.data_dir)
    if arguments.command == "db":
        paths.ensure_directories()
        run_migrations(paths)
        raise SystemExit(0)
    run_server(
        paths,
        arguments.port,
        additional_hosts=arguments.hosts,
        open_browser=True,
        verbose=arguments.verbose,
    )
    raise SystemExit(0)
