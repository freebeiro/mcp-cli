"""
Common test fixtures and configuration for all tests.
"""

import pytest
import os
import json
from typing import Dict, Any

@pytest.fixture
def test_config() -> Dict[str, Any]:
    """Load test configuration."""
    config_path = os.path.join(os.path.dirname(__file__), "..", "test_config.json")
    with open(config_path) as f:
        return json.load(f)

@pytest.fixture
def test_data_dir() -> str:
    """Return path to test data directory."""
    return os.path.join(os.path.dirname(__file__), "fixtures")
