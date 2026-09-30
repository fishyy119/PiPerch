from __future__ import annotations

import argparse
import os
import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn, Protocol

import uvicorn

from piperch.app import create_app
from piperch.database import run_migrations
from piperch.paths import AppPaths

_GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS = 5

if TYPE_CHECKING:
    from collections.abc import Callable


class _ServerControl(Protocol):
    should_exit: bool
    force_exit: bool


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


def _start_terminal_interrupt_watcher(server: _ServerControl) -> None:
    if os.name != "nt" or not sys.stdin.isatty():
        return
    import msvcrt

    threading.Thread(
        target=watch_terminal_interrupts,
        args=(msvcrt.getwch, server),
        name="piperch-terminal-interrupt",
        daemon=True,
    ).start()


def run_server(paths: AppPaths, port: int) -> None:
    config = uvicorn.Config(
        create_app(paths),
        host="127.0.0.1",
        port=port,
        workers=1,
        timeout_graceful_shutdown=_GRACEFUL_SHUTDOWN_TIMEOUT_SECONDS,
    )
    server = uvicorn.Server(config)
    _start_terminal_interrupt_watcher(server)
    server.run()
    if not server.started:
        raise SystemExit(3)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="piperch", description="PiPerch 本地 Pixiv 管理器")
    commands = parser.add_subparsers(dest="command", required=True)

    serve = commands.add_parser("serve", help="迁移数据库并启动本地服务")
    serve.add_argument("--port", type=int, default=6999)
    serve.add_argument("--data-dir", type=Path)

    database = commands.add_parser("db", help="数据库管理")
    database.add_argument("action", choices=["upgrade"])
    database.add_argument("--data-dir", type=Path)
    return parser


def main() -> NoReturn:
    arguments = _parser().parse_args()
    paths = AppPaths.from_data_dir(arguments.data_dir)
    if arguments.command == "db":
        paths.ensure_directories()
        run_migrations(paths)
        raise SystemExit(0)
    if not 1 <= arguments.port <= 65535:
        _parser().error("端口必须位于 1 到 65535 之间。")
    run_server(paths, arguments.port)
    raise SystemExit(0)
