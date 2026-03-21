"""Shared fixtures for rakopy tests."""
# pylint: disable=protected-access

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from rakopy.hub import Hub


def make_reader(responses: list[bytes]) -> AsyncMock:
    """Create a mock StreamReader that returns predefined responses."""
    reader = AsyncMock(spec=asyncio.StreamReader)
    reader.readline = AsyncMock(side_effect=responses)
    return reader


def make_writer() -> MagicMock:
    """Create a mock StreamWriter with a working drain and transport."""
    writer = MagicMock(spec=asyncio.StreamWriter)
    writer.write = MagicMock()
    writer.drain = AsyncMock()
    writer.transport = MagicMock()
    writer.transport.is_closing.return_value = False
    return writer


def json_line(data: dict) -> bytes:
    """Encode a dict as a JSON line (bytes) as the hub would send."""
    return (json.dumps(data) + "\r\n").encode()


@pytest.fixture
def hub():
    """Return a Hub instance with mocked connection."""
    return Hub("test_client", "192.168.1.42")


@pytest.fixture
def connected_hub():
    """Return a Hub that appears already connected (writer.transport exists)."""
    hub_instance = Hub("test_client", "192.168.1.42")
    hub_instance._writer = make_writer()
    hub_instance._reader = make_reader([])
    return hub_instance
