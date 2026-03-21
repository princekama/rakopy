"""Tests for rakopy.errors."""
# pylint: disable=missing-class-docstring,missing-function-docstring

import pytest

from rakopy.errors import ConfigValidationError, SendCommandError


class TestConfigValidationError:
    def test_is_exception(self):
        assert issubclass(ConfigValidationError, Exception)

    def test_message(self):
        with pytest.raises(ConfigValidationError, match="bad config"):
            raise ConfigValidationError("bad config")


class TestSendCommandError:
    def test_is_exception(self):
        assert issubclass(SendCommandError, Exception)

    def test_message(self):
        with pytest.raises(SendCommandError, match="command failed"):
            raise SendCommandError("command failed")
