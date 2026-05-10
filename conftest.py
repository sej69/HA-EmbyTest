"""Root conftest — runs before any plugin or test collection."""

from __future__ import annotations

import asyncio
import sys


def pytest_configure(config: object) -> None:
    """Make the HA test framework work on Windows.

    Two problems need solving:

    1. HassEventLoopPolicy (set and locked by pytest-homeassistant-custom-component)
       extends asyncio.DefaultEventLoopPolicy which on Windows is
       ProactorEventLoopPolicy. Swapping its base class to
       WindowsSelectorEventLoopPolicy makes new_event_loop() produce a
       SelectorEventLoop instead, which the HA test helpers expect.

    2. SelectorEventLoop._make_self_pipe() calls socket.socketpair() using
       AF_INET on Windows (AF_UNIX does not exist there). pytest-socket,
       loaded by pytest-homeassistant-custom-component, blocks all AF_INET
       socket creation. We patch _make_self_pipe to temporarily restore the
       real socket.socket (saved by pytest_socket before its own patching)
       for the duration of self-pipe initialisation only.
    """
    if sys.platform != "win32":
        return

    import socket as _socket
    from asyncio import selector_events

    import pytest_socket
    from homeassistant import runner

    # Fix 1 — use SelectorEventLoop as the base on Windows.
    runner.HassEventLoopPolicy.__bases__ = (asyncio.WindowsSelectorEventLoopPolicy,)

    # Fix 2 — allow self-pipe socket creation during event loop init.
    _original_make_self_pipe = selector_events.BaseSelectorEventLoop._make_self_pipe  # type: ignore[attr-defined]

    def _make_self_pipe_windows(self: selector_events.BaseSelectorEventLoop) -> None:  # type: ignore[override]
        old = _socket.socket
        _socket.socket = pytest_socket._true_socket
        try:
            _original_make_self_pipe(self)
        finally:
            _socket.socket = old

    selector_events.BaseSelectorEventLoop._make_self_pipe = _make_self_pipe_windows  # type: ignore[attr-defined]
