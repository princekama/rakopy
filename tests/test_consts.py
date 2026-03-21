"""Tests for rakopy.consts."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from rakopy.consts import DEFAULT_PORT


def test_default_port():
    assert DEFAULT_PORT == 9762
