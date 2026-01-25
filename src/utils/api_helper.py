"""
API helper to switch between real and mock API
"""
from src.config import USE_MOCK_API


def get_api_class():
    """Get API class (real or mock) based on config"""
    if USE_MOCK_API:
        from src.utils.mock_api import MockAPI
        return MockAPI
    else:
        from py4writers import API
        return API
