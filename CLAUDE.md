# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

RakoPy is an async Python library for controlling [Rako](https://rakocontrols.com) smart lighting systems via their hub (WK-HUB / RK-HUB). It communicates over a TCP/JSON protocol on port 9762, using `asyncio.StreamReader`/`StreamWriter` for all I/O. The protocol spec is documented in `docs/accessing-the-rako-hub.pdf`.

Requires Python >= 3.12.

## Build, Test, and Lint

Always activate the virtual environment first; there is no build step — the library is pure Python.

```bash
source .venv/bin/activate
pip install pylint pytest pytest-asyncio

# Lint (matches CI exactly)
pylint $(git ls-files '*.py')

# Run all tests
pytest tests/ -v

# Run a single test file / class / method
pytest tests/test_hub.py -v
pytest tests/test_hub.py::TestSetRgb -v
pytest tests/test_hub.py::TestSetRgb::test_set_rgb_default -v
```

Pytest is configured via `[tool.pytest.ini_options] pythonpath = ["src"]` in `pyproject.toml`, so tests import `rakopy` directly from `src/` without installing the package. An editable install would require `src/rakopy/__version__.py` to exist (CI generates this on release from the git tag).

## Architecture

The entire library lives in `src/rakopy/`:

- **`hub.py`** — The `Hub` class is the sole public API. It opens a TCP connection to the Rako hub and exchanges line-delimited JSON (`\r\n` terminated). All network-touching methods are `async`. Connection management uses `asyncio.Lock` for thread safety and auto-reconnects when the transport is closing.
- **`model.py`** — Plain `@dataclass` response/event types: `Room`, `Channel`, `Scene`, `Level`, `ChannelLevel`, `LevelInfo`, `HubStatus`, `LevelChangedEvent`, `SceneChangedEvent`.
- **`consts.py`** — Protocol constants (currently just `DEFAULT_PORT = 9762`).
- **`errors.py`** — `ConfigValidationError` (init validation) and `SendCommandError` (hub error responses).

### Hub communication flow

1. **Connect** → `asyncio.open_connection(host, port)`
2. **Subscribe** → Send `SUB,JSON,{...}\r\n` with client name and subscription list
3. **Command/Query** → Send JSON line, read JSON line response
4. **Events** → `get_events()` is an `AsyncGenerator` that subscribes to `TRACKER` and yields `SceneChangedEvent` / `LevelChangedEvent` objects

### Conventions

- **Async throughout** — Tests use `pytest-asyncio` with `@pytest.mark.asyncio`.
- **Static conversion methods** — `Hub._to_room()` and `Hub._to_level()` are `@staticmethod` and convert raw JSON dicts to dataclasses. They handle edge cases like inheriting `colorType` from the first channel in multi-channel RGB groups, and always prepending a Scene 0 ("Off").
- **Mocked TCP in tests** — Tests never open real connections. They use `unittest.mock.AsyncMock` for `StreamReader`/`StreamWriter` plus helpers in `tests/helpers.py` (`make_reader`, `make_writer`, `json_line`), wired through `tests/conftest.py`. Pattern: patch `_reconnect` as a no-op, set `hub._reader`/`hub._writer` to mocks, then call the method under test.
- **Pylint config** — `.pylintrc` raises `max-args=8`, `max-attributes=8`, `max-positional-arguments=8` to accommodate the Hub API's parameter-heavy methods.
