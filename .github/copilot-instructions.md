# Copilot Instructions for RakoPy

## Overview

RakoPy is an async Python library for controlling [Rako](https://rakocontrols.com) smart lighting systems via their hub (WK-HUB / RK-HUB). It communicates over a TCP/JSON protocol on port 9762, using `asyncio.StreamReader`/`StreamWriter` for all I/O.

## Build, Test, and Lint

```bash
# Set up virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install pylint pytest pytest-asyncio

# Lint (matches CI)
pylint $(git ls-files '*.py')

# Run all tests
pytest tests/ -v

# Run a single test file
pytest tests/test_hub.py -v

# Run a single test class or method
pytest tests/test_hub.py::TestSetRgb -v
pytest tests/test_hub.py::TestSetRgb::test_set_rgb_default -v
```

Always use a virtual environment (`.venv`) when running commands. There is no build step — the library is pure Python. The project uses Hatch as its build backend (`pyproject.toml`), but editable installs require `src/rakopy/__version__.py` to exist. Pytest is configured via `[tool.pytest.ini_options] pythonpath = ["src"]` in `pyproject.toml`, so tests can import `rakopy` directly from `src/` without installing the package.

## Architecture

The entire library lives in `src/rakopy/` with four modules:

- **`hub.py`** — The `Hub` class is the sole public API. It opens a TCP connection to the Rako hub and exchanges line-delimited JSON (`\r\n` terminated). All methods are `async`. Connection management uses `asyncio.Lock` for thread safety and auto-reconnects when the transport is closing.
- **`model.py`** — Plain `@dataclass` classes representing hub responses: `Room`, `Channel`, `Scene`, `Level`, `ChannelLevel`, `LevelInfo`, `HubStatus`, and event types (`LevelChangedEvent`, `SceneChangedEvent`).
- **`consts.py`** — Protocol constants (currently just `DEFAULT_PORT = 9762`).
- **`errors.py`** — Two exception classes: `ConfigValidationError` (init validation) and `SendCommandError` (hub error responses).

### Hub communication flow

1. **Connect** → `asyncio.open_connection(host, port)`
2. **Subscribe** → Send `SUB,JSON,{...}\r\n` with client name and subscription list
3. **Command/Query** → Send JSON line, read JSON line response
4. **Events** → `get_events()` is an `AsyncGenerator` that subscribes to `TRACKER` and yields `SceneChangedEvent` / `LevelChangedEvent` objects

The protocol spec is documented in `docs/accessing-the-rako-hub.pdf`.

## Key Conventions

- **Async throughout** — Every Hub method that touches the network is `async`. Tests use `pytest-asyncio` with `@pytest.mark.asyncio`.
- **Static conversion methods** — `Hub._to_room()` and `Hub._to_level()` are `@staticmethod` methods that convert raw JSON dicts to dataclass instances. They handle edge cases like inheriting `colorType` from the first channel in multi-channel RGB groups, and always prepending a Scene 0 ("Off").
- **Mocked TCP in tests** — Tests never open real connections. They use `unittest.mock.AsyncMock` for `StreamReader`/`StreamWriter` and helper functions from `tests/conftest.py` (`make_reader`, `make_writer`, `json_line`). The pattern is: patch `_reconnect` as a no-op, set `hub._reader`/`hub._writer` to mocks, then call the method under test.
- **Pylint config** — `.pylintrc` raises limits to `max-args=8`, `max-attributes=8`, `max-positional-arguments=8` to accommodate the Hub API's parameter-heavy methods.
