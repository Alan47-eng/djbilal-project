import pytest

# Configure pytest-asyncio with auto mode
pytest_plugins = ('pytest_asyncio',)

def pytest_configure(config):
    """Configure pytest with asyncio mode"""
    config.option.asyncio_mode = "auto"
