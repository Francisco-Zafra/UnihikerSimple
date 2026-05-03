"""Open-Meteo weather client used by the clock view."""

import json
import ssl
import threading
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from urllib.error import URLError


WEATHER_CODE_ES = {
    0: "DESPEJADO",
    1: "POCO NUBOSO",
    2: "NUBES",
    3: "CUBIERTO",
    45: "NIEBLA",
    48: "NIEBLA",
    51: "LLOVIZNA",
    53: "LLOVIZNA",
    55: "LLOVIZNA",
    56: "HIELO",
    57: "HIELO",
    61: "LLUVIA",
    63: "LLUVIA",
    65: "LLUVIA",
    66: "HIELO",
    67: "HIELO",
    71: "NIEVE",
    73: "NIEVE",
    75: "NIEVE",
    77: "NIEVE",
    80: "CHUBASCOS",
    81: "CHUBASCOS",
    82: "CHUBASCOS",
    85: "NIEVE",
    86: "NIEVE",
    95: "TORMENTA",
    96: "TORMENTA",
    99: "TORMENTA",
}


def urlopen_with_cert_fallback(url, timeout):
    try:
        return urllib.request.urlopen(url, timeout=timeout)
    except URLError as exc:
        if not isinstance(exc.reason, ssl.SSLCertVerificationError):
            raise

        context = ssl._create_unverified_context()
        return urllib.request.urlopen(url, timeout=timeout, context=context)


@dataclass
class WeatherState:
    temperature: float | None = None
    humidity: int | None = None
    wind_speed: float | None = None
    weather_code: int | None = None
    fetched_at: datetime | None = None
    error: str | None = None
    loading: bool = False

    @property
    def condition(self):
        return WEATHER_CODE_ES.get(self.weather_code, "CLIMA")


class WeatherClient:
    def __init__(self, config):
        self.config = config
        self.state = WeatherState()
        self._elapsed = float(config["weather_refresh_seconds"])
        self._thread = None
        self._lock = threading.Lock()

    def update(self, dt):
        if not self.config["weather_enabled"]:
            return

        self._elapsed += dt
        if self._elapsed >= self.config["weather_refresh_seconds"]:
            self._elapsed = 0.0
            self.fetch_async()

    def fetch_async(self):
        if self._thread and self._thread.is_alive():
            return

        with self._lock:
            self.state.loading = True
            self.state.error = None

        self._thread = threading.Thread(target=self._fetch, daemon=True)
        self._thread.start()

    def _fetch(self):
        params = {
            "latitude": self.config["weather_latitude"],
            "longitude": self.config["weather_longitude"],
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "timezone": "auto",
        }
        url = "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)

        try:
            with urlopen_with_cert_fallback(url, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))

            current = payload["current"]
            state = WeatherState(
                temperature=float(current["temperature_2m"]),
                humidity=int(current["relative_humidity_2m"]),
                wind_speed=float(current["wind_speed_10m"]),
                weather_code=int(current["weather_code"]),
                fetched_at=datetime.now(),
                loading=False,
            )
        except (OSError, KeyError, ValueError, json.JSONDecodeError):
            state = WeatherState(error="SIN DATOS", loading=False)

        with self._lock:
            self.state = state

    def snapshot(self):
        with self._lock:
            return WeatherState(
                temperature=self.state.temperature,
                humidity=self.state.humidity,
                wind_speed=self.state.wind_speed,
                weather_code=self.state.weather_code,
                fetched_at=self.state.fetched_at,
                error=self.state.error,
                loading=self.state.loading,
            )
