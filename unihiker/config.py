"""Small JSON-backed app configuration."""

import json
from datetime import date

from .paths import CONFIG_PATH

DEFAULT_CONFIG = {
    "auto_switch_seconds": 5 * 60,
    "web_enabled": True,
    "web_host": "0.0.0.0",
    "web_port": 8123,
    "view_order": ["homeload", "clock", "investment", "quote"],
    "weather_enabled": True,
    "weather_label": "Benalmadena",
    "weather_latitude": 36.5988,
    "weather_longitude": -4.5168,
    "weather_refresh_seconds": 15 * 60,
    "buzzer_enabled": False,
    "investment_label": "Fidelity MSCI World",
    "investment_symbol": "0P0001CLDK.F",
    "investment_start_date": "2025-05-16",
    "investment_refresh_seconds": 6 * 60 * 60,
    "quote_url": "https://frasedeldia.azurewebsites.net/api/phrase",
    "quote_refresh_seconds": 24 * 60 * 60,
}


def load_config():
    if not CONFIG_PATH.exists():
        return dict(DEFAULT_CONFIG)

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULT_CONFIG)

    config = dict(DEFAULT_CONFIG)
    config.update({key: value for key, value in data.items() if key in config})
    if not isinstance(config["auto_switch_seconds"], (int, float)):
        config["auto_switch_seconds"] = DEFAULT_CONFIG["auto_switch_seconds"]
    if not isinstance(config["web_enabled"], bool):
        config["web_enabled"] = DEFAULT_CONFIG["web_enabled"]
    if not isinstance(config["web_host"], str):
        config["web_host"] = DEFAULT_CONFIG["web_host"]
    if not isinstance(config["web_port"], (int, float)):
        config["web_port"] = DEFAULT_CONFIG["web_port"]
    if not isinstance(config["view_order"], list):
        config["view_order"] = list(DEFAULT_CONFIG["view_order"])
    if not isinstance(config["weather_enabled"], bool):
        config["weather_enabled"] = DEFAULT_CONFIG["weather_enabled"]
    if not isinstance(config["weather_label"], str):
        config["weather_label"] = DEFAULT_CONFIG["weather_label"]
    if not isinstance(config["weather_latitude"], (int, float)):
        config["weather_latitude"] = DEFAULT_CONFIG["weather_latitude"]
    if not isinstance(config["weather_longitude"], (int, float)):
        config["weather_longitude"] = DEFAULT_CONFIG["weather_longitude"]
    if not isinstance(config["weather_refresh_seconds"], (int, float)):
        config["weather_refresh_seconds"] = DEFAULT_CONFIG["weather_refresh_seconds"]
    if not isinstance(config["buzzer_enabled"], bool):
        config["buzzer_enabled"] = DEFAULT_CONFIG["buzzer_enabled"]
    if not isinstance(config["investment_label"], str):
        config["investment_label"] = DEFAULT_CONFIG["investment_label"]
    if not isinstance(config["investment_symbol"], str):
        config["investment_symbol"] = DEFAULT_CONFIG["investment_symbol"]
    if not isinstance(config["investment_start_date"], str):
        config["investment_start_date"] = DEFAULT_CONFIG["investment_start_date"]
    if not isinstance(config["investment_refresh_seconds"], (int, float)):
        config["investment_refresh_seconds"] = DEFAULT_CONFIG["investment_refresh_seconds"]
    if not isinstance(config["quote_url"], str):
        config["quote_url"] = DEFAULT_CONFIG["quote_url"]
    if not isinstance(config["quote_refresh_seconds"], (int, float)):
        config["quote_refresh_seconds"] = DEFAULT_CONFIG["quote_refresh_seconds"]

    config["auto_switch_seconds"] = max(10, int(config["auto_switch_seconds"]))
    config["web_port"] = min(65535, max(1, int(config["web_port"])))
    config["view_order"] = [
        name for name in config["view_order"]
        if isinstance(name, str) and name in DEFAULT_CONFIG["view_order"]
    ]
    if not config["view_order"]:
        config["view_order"] = list(DEFAULT_CONFIG["view_order"])
    config["weather_latitude"] = float(config["weather_latitude"])
    config["weather_longitude"] = float(config["weather_longitude"])
    config["weather_refresh_seconds"] = max(60, int(config["weather_refresh_seconds"]))
    try:
        date.fromisoformat(config["investment_start_date"])
    except ValueError:
        config["investment_start_date"] = DEFAULT_CONFIG["investment_start_date"]
    config["investment_refresh_seconds"] = max(300, int(config["investment_refresh_seconds"]))
    config["quote_refresh_seconds"] = max(3600, int(config["quote_refresh_seconds"]))
    return config


def save_config(config):
    data = dict(DEFAULT_CONFIG)
    data.update({key: value for key, value in config.items() if key in data})

    with CONFIG_PATH.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")
