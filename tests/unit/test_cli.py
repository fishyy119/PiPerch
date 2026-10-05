from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from piperch.cli import run_server, watch_terminal_interrupts
from piperch.paths import AppPaths

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from pytest import MonkeyPatch

    from piperch.runtime import AppControl


class FakeServer:
    instances: ClassVar[list[FakeServer]] = []

    def __init__(self, config: object) -> None:
        self.config = config
        self.should_exit = False
        self.force_exit = False
        self.started = True
        self.ran = False
        self.sockets: list[object] | None = None
        self.instances.append(self)

    def run(self, sockets: list[object] | None = None) -> None:
        self.ran = True
        self.sockets = sockets


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
    assert FakeServer.instances[0].sockets is None


def test_run_server_adds_explicit_hosts_to_loopback_listener(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    @dataclass(frozen=True)
    class FakeSocket:
        host: str
        port: int

        def close(self) -> None:
            pass

    def fake_bind_sockets(hosts: Sequence[str], port: int) -> list[FakeSocket]:
        return [FakeSocket(host, port) for host in hosts]

    FakeServer.instances.clear()
    monkeypatch.setattr("piperch.cli.uvicorn.Server", FakeServer)
    monkeypatch.setattr("piperch.cli._bind_sockets", fake_bind_sockets)

    def ignore_watcher(_server: object) -> None:
        pass

    monkeypatch.setattr("piperch.cli._start_terminal_interrupt_watcher", ignore_watcher)

    run_server(
        AppPaths.from_data_dir(tmp_path),
        7000,
        additional_hosts=("192.168.1.10", "127.0.0.1", "192.168.1.10"),
    )

    sockets = FakeServer.instances[0].sockets or []
    assert len(sockets) == 2
    assert set(sockets) == {FakeSocket("127.0.0.1", 7000), FakeSocket("192.168.1.10", 7000)}


def test_run_server_recreates_application_after_restart_request(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    controls: list[AppControl] = []
    watcher_calls: list[object] = []

    def fake_create_app(_paths: AppPaths, control: AppControl) -> object:
        controls.append(control)
        return object()

    def fake_config(_app: object, **_kwargs: object) -> object:
        return object()

    def record_watcher(lifecycle: object) -> None:
        watcher_calls.append(lifecycle)

    class RestartingServer(FakeServer):
        def run(self, sockets: list[object] | None = None) -> None:
            self.ran = True
            self.sockets = sockets
            if len(self.instances) == 1:
                controls[-1].request_restart()

    FakeServer.instances.clear()
    monkeypatch.setattr("piperch.cli.create_app", fake_create_app)
    monkeypatch.setattr("piperch.cli.uvicorn.Config", fake_config)
    monkeypatch.setattr("piperch.cli.uvicorn.Server", RestartingServer)
    monkeypatch.setattr("piperch.cli._start_terminal_interrupt_watcher", record_watcher)

    run_server(AppPaths.from_data_dir(tmp_path), 7000)

    assert len(RestartingServer.instances) == 2
    assert len(controls) == 2
    assert len(watcher_calls) == 1


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
