"""Tests for rakopy.consts."""
# pylint: disable=missing-function-docstring

from rakopy.consts import DEFAULT_PORT


def test_default_port():
    assert DEFAULT_PORT == 9762
