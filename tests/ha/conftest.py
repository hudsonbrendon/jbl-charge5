"""Fixtures for JBL Charge 5 HA tests."""

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom integrations in all tests."""
    yield


@pytest.fixture(autouse=True)
def auto_mock_bluetooth(mock_bluetooth_adapters, mock_bleak_scanner_start):
    """Keep HA's bluetooth stack off the real BlueZ/HCI sockets (Linux CI)."""
    yield
