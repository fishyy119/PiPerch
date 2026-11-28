from __future__ import annotations

import argparse
import logging
import os
import re
import socket
import sys
import threading
import webbrowser
from contextlib import ExitStack
from dataclasses import InitVar, dataclass, field
from ipaddress import AddressValueError, IPv4Address
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn, Protocol
from uuid import uuid4

_GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS = 5
_LOOPBACK_HOST = "127.0.0.1"

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from typing import Any


@dataclass(slots=True)
class Args:
    """声明并校验命令行参数，向程序提供类型明确的配置。"""

    data_dir: Path | None = None
    port: int = 9303
    hosts: list[str] = field(default_factory=list[str])
    verbose: bool = False
    http2: bool = False
    cert_dir: InitVar[Path | None] = None
    browser_host: str = field(init=False, default=_LOOPBACK_HOST)
    ssl_certfile: Path | None = field(init=False, default=None)
    ssl_keyfile: Path | None = field(init=False, default=None)

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--port")
        parser.add_argument(
            "--host",
            dest="hosts",
            action="append",
            metavar="IP",
            help="追加监听的本机 IPv4 地址，可重复传入，始终监听 127.0.0.1",
        )
        parser.add_argument("--data-dir", help="程序数据目录，用于保存数据库、设置和缓存等，默认为 ~/.piperch")
        parser.add_argument("--verbose", action="store_true", help="输出每个 HTTP 请求的访问日志")
        parser.add_argument("--http2", action="store_true", help="在 HTTPS 上启用实验性 HTTP/2，需要 --cert-dir")
        parser.add_argument("--cert-dir", type=Path, metavar="DIR", help="包含 PEM 证书链和私钥的 HTTPS 目录")

    @classmethod
    def from_ns(cls, namespace: argparse.Namespace) -> Args:
        return cls(**vars(namespace))

    def __post_init__(self, cert_dir: Path | None) -> None:
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

        if cert_dir is not None:
            self.browser_host, self.ssl_certfile, self.ssl_keyfile = self._find_certificate(cert_dir)
        elif self.http2:
            raise ValueError("启用 HTTP/2 需要通过 --cert-dir 指定 HTTPS 证书目录。")

    @staticmethod
    def _find_certificate(cert_dir: Path) -> tuple[str, Path, Path]:
        if not cert_dir.is_dir():
            raise ValueError(f"无法访问 HTTPS 证书目录 {cert_dir}。")

        for chain in sorted(cert_dir.glob("*-chain.pem", case_sensitive=True), key=lambda path: path.name):
            prefix = chain.name.removesuffix("-chain.pem")
            key = chain.with_name(f"{prefix}-key.pem")
            if chain.is_file() and key.is_file():
                return Args._certificate_host(chain), chain, key

        raise ValueError("HTTPS 证书目录必须包含至少一组 <前缀>-chain.pem 和 <前缀>-key.pem。")

    @staticmethod
    def _certificate_host(chain: Path) -> str:
        from cryptography import x509

        try:
            certificate = x509.load_pem_x509_certificate(chain.read_bytes())
            names = certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        except (OSError, ValueError, x509.ExtensionNotFound, x509.DuplicateExtension) as error:
            raise ValueError(f"无法读取 HTTPS 站点证书 {chain} 的 SAN。{error}") from error

        for name in names:
            if isinstance(name, x509.DNSName) and re.fullmatch(r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*", name.value):
                return name.value
            if isinstance(name, x509.IPAddress) and isinstance(name.value, IPv4Address):
                return str(name.value)

        raise ValueError(f"HTTPS 站点证书 {chain} 的 SAN 中没有具体的域名或 IPv4 地址。")

    @classmethod
    def parse(cls) -> Args:
        parser = argparse.ArgumentParser(
            prog="piperch", description="PiPerch 本地 Pixiv 管理器", argument_default=argparse.SUPPRESS
        )
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
    from copy import deepcopy

    from uvicorn.config import LOGGING_CONFIG

    config = deepcopy(LOGGING_CONFIG)
    for formatter in config["formatters"].values():
        formatter["fmt"] = "%(asctime)s " + formatter["fmt"]
        formatter["datefmt"] = "%m%d %H:%M:%S"
    config["loggers"]["piperch"] = {
        "handlers": ["default"],
        "level": "INFO",
        "propagate": False,
    }
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


def run_server(args: Args, *, open_browser: bool = False) -> None:
    import uvicorn

    from .app import create_app
    from .application.control import AppControl
    from .paths import AppPaths

    paths = AppPaths.from_data_dir(args.data_dir)
    scheme = "https" if args.ssl_certfile is not None else "http"
    lifecycle = _ServerLifecycle()
    hosts = tuple(dict.fromkeys((_LOOPBACK_HOST, *args.hosts)))
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
            port=args.port,
            http="zttp" if args.http2 else "auto",
            http2=args.http2,
            ssl_certfile=args.ssl_certfile,
            ssl_keyfile=args.ssl_keyfile,
            workers=1,
            timeout_graceful_shutdown=_GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS,
            log_config=_logging_config(verbose=args.verbose),
            access_log=True,
        )
        if args.ssl_certfile is not None:
            try:
                config.load()
            except OSError as error:
                raise SystemExit(f"无法加载 HTTPS 证书或私钥。{error}") from None
        server = uvicorn.Server(config)
        try:
            sockets = _bind_sockets(hosts, args.port) if len(hosts) > 1 else []
        except OSError as error:
            logging.getLogger("uvicorn.error").error(error)
            raise SystemExit(3) from None
        if sockets:
            logger = logging.getLogger("uvicorn.error")
            for host in hosts:
                logger.info("Uvicorn running on %s://%s:%d (Press CTRL+C to quit)", scheme, host, args.port)
        if open_browser:
            threading.Timer(
                1,
                webbrowser.open,
                args=(f"{scheme}://{args.browser_host}:{config.port}",),
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
    run_server(arguments, open_browser=True)
    raise SystemExit(0)
