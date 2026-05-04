"""Backward-compatible dataflow config helpers."""

from pathlib import Path

from tradingagents.config.config_manager import config_manager


def initialize_config():
    config_manager.ensure_directories_exist()
    return config_manager.load_settings()


def get_data_dir() -> str:
    return config_manager.get_data_dir()


def set_data_dir(data_dir: str):
    config_manager.set_data_dir(data_dir)
    Path(data_dir).mkdir(parents=True, exist_ok=True)
    config_manager.ensure_directories_exist()


def get_config():
    return config_manager.load_settings()


def set_config(config):
    config_manager.save_settings(config)


__all__ = [
    "initialize_config",
    "get_data_dir",
    "set_data_dir",
    "get_config",
    "set_config",
]
