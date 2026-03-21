"""Shared fixtures for rakopy tests."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

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
    h = Hub("test_client", "192.168.1.42")
    h._writer = make_writer()
    h._reader = make_reader([])
    return h
