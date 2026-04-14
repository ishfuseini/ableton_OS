"""Tests for config module."""

from abletonos.config import AbletonOSConfig


def test_config_library_root_defaults_none():
    config = AbletonOSConfig(project_root="/music")
    assert config.library_root is None


def test_config_library_root_round_trips():
    config = AbletonOSConfig(
        project_root="/music",
        library_root="/samples",
        pocketbase_url="http://localhost:8090",
    )
    d = config.to_dict()
    restored = AbletonOSConfig.from_dict(d)
    assert restored.library_root == "/samples"


def test_config_from_dict_missing_library_root():
    """Existing configs without library_root should still load."""
    data = {"project_root": "/music", "pocketbase_url": None}
    config = AbletonOSConfig.from_dict(data)
    assert config.library_root is None
