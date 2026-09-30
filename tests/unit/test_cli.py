from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from piperch.cli import run_server, watch_terminal_interrupts
from piperch.paths import AppPaths

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch


class FakeServer:
    instances: ClassVar[list[FakeServer]] = []

    def __init__(self, config: object) -> None:
        self.config = config
        self.should_exit = False
        self.force_exit = False
        self.started = True
        self.ran = False
        self.instances.append(self)

    def run(self) -> None:
        self.ran = True


def test_run_server_uses_bounded_graceful_shutdown(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    configs: list[dict[str, object]] = []

    def fake_config(app: object, **kwargs: object) -> object:
        configs.append({"app": app, **kwargs})
        return object()

    FakeServer.instances.clear()
    monkeypatch.setattr("piperch.cli.uvicorn.Config", fake_config)
    monkeypatch.setattr("piperch.cli.uvicorn.Server", FakeServer)

    def ignore_watcher(_server: object) -> None:
        pass

    monkeypatch.setattr("piperch.cli._start_terminal_interrupt_watcher", ignore_watcher)

    run_server(AppPaths.from_data_dir(tmp_path), 7000)

    assert configs[0]["host"] == "127.0.0.1"
    assert configs[0]["port"] == 7000
    assert configs[0]["workers"] == 1
    assert configs[0]["timeout_graceful_shutdown"] == 5
    assert FakeServer.instances[0].ran


def test_terminal_interrupt_requests_graceful_then_forced_exit() -> None:
    server = FakeServer(object())
    characters = iter(("\x03", "\x03"))

    watch_terminal_interrupts(lambda: next(characters, ""), server)

    assert server.should_exit
    assert server.force_exit


def test_first_terminal_interrupt_does_not_duplicate_a_signal() -> None:
    server = FakeServer(object())
    server.should_exit = True
    characters = iter(("\x03", ""))

    watch_terminal_interrupts(lambda: next(characters, ""), server)

    assert not server.force_exit
