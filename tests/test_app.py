"""Tests for pytop application."""

import pytest

from pytop.app import PytopApp, format_bytes


def test_format_bytes_bytes():
    """Test format_bytes with byte values."""
    assert "B" in format_bytes(500)


def test_format_bytes_kilobytes():
    """Test format_bytes with kilobyte values."""
    result = format_bytes(2048)
    assert "K" in result


def test_format_bytes_megabytes():
    """Test format_bytes with megabyte values."""
    result = format_bytes(5242880)
    assert "M" in result


def test_format_bytes_gigabytes():
    """Test format_bytes with gigabyte values."""
    result = format_bytes(1073741824)
    assert "G" in result


@pytest.mark.asyncio
async def test_app_creation():
    """Test PytopApp can be instantiated."""
    app = PytopApp()
    assert app.title == "pytop"
    assert app.sub_title == "Python System Monitor"


@pytest.mark.asyncio
async def test_app_compose():
    """Test PytopApp composes correctly."""
    app = PytopApp()
    async with app.run_test() as pilot:
        # Verify the app has the expected widgets
        assert pilot.app.query_one("#header-stats") is not None
        assert pilot.app.query_one("#process-table") is not None


@pytest.mark.asyncio
async def test_app_quit_binding():
    """Test that 'q' binding triggers quit."""
    app = PytopApp()
    async with app.run_test() as pilot:
        await pilot.press("q")
        # App should be exiting
        assert pilot.app._exit
