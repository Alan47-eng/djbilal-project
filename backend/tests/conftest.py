import os

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-local-pytest-only")
os.environ.setdefault("ADMIN_PASSWORD", "TestAdminPass123")

# Configure pytest-asyncio with auto mode
pytest_plugins = ('pytest_asyncio',)

def pytest_configure(config):
    """Configure pytest with asyncio mode"""
    config.option.asyncio_mode = "auto"
