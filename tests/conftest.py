"""Shared fixtures for rakopy tests."""
# pylint: disable=protected-access

import pytest

from rakopy.hub import Hub
from tests.helpers import make_reader, make_writer


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
