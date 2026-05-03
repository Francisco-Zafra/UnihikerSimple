"""Yahoo Finance chart client for the investment view."""

import json
import ssl
import threading
import urllib.parse
import urllib.request
from urllib.error import URLError
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from pathlib import Path


CACHE_DIR = Path(__file__).with_name(".cache")


def urlopen_with_cert_fallback(request, timeout):
    try:
        return urllib.request.urlopen(request, timeout=timeout)
    except URLError as exc:
        if not isinstance(exc.reason, ssl.SSLCertVerificationError):
            raise

        context = ssl._create_unverified_context()
        return urllib.request.urlopen(request, timeout=timeout, context=context)


@dataclass
class InvestmentPoint:
    day: date
    close: float


@dataclass
class InvestmentState:
    points: list[InvestmentPoint]
    fetched_at: datetime | None = None
    error: str | None = None
    loading: bool = False

    @property
    def first(self):
        return self.points[0] if self.points else None

    @property
    def last(self):
        return self.points[-1] if self.points else None

    @property
    def percent_change(self):
        if not self.first or not self.last or self.first.close == 0:
            return None
        return (self.last.close / self.first.close - 1) * 100

    def percent_change_since_days(self, days):
        if not self.last or not self.points:
            return None

        target = self.last.day.toordinal() - days
        base = self.points[0]
        for point in self.points:
            if point.day.toordinal() >= target:
                base = point
                break

        if base.close == 0:
            return None
        return (self.last.close / base.close - 1) * 100


class InvestmentClient:
    def __init__(self, config):
        self.config = config
        self.state = InvestmentState(points=[])
        self._elapsed = float(config["investment_refresh_seconds"])
        self._thread = None
        self._lock = threading.Lock()
        self._load_cache()

    def update(self, dt):
        self._elapsed += dt
        if self._elapsed >= self.config["investment_refresh_seconds"]:
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

    def snapshot(self):
        with self._lock:
            return InvestmentState(
                points=list(self.state.points),
                fetched_at=self.state.fetched_at,
                error=self.state.error,
                loading=self.state.loading,
            )

    def _cache_path(self):
        symbol = self.config["investment_symbol"].replace("/", "_")
        return CACHE_DIR / f"{symbol}.json"

    def _load_cache(self):
        path = self._cache_path()
        if not path.exists():
            return

        try:
            with path.open("r", encoding="utf-8") as fh:
                payload = json.load(fh)
            points = [
                InvestmentPoint(date.fromisoformat(item["date"]), float(item["close"]))
                for item in payload.get("points", [])
            ]
            fetched_at = datetime.fromisoformat(payload["fetched_at"]) if payload.get("fetched_at") else None
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return

        self.state = InvestmentState(points=points, fetched_at=fetched_at)

    def _save_cache(self, state):
        CACHE_DIR.mkdir(exist_ok=True)
        payload = {
            "fetched_at": state.fetched_at.isoformat() if state.fetched_at else None,
            "points": [
                {"date": point.day.isoformat(), "close": point.close}
                for point in state.points
            ],
        }

        with self._cache_path().open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
            fh.write("\n")

    def _fetch(self):
        try:
            points = self._fetch_points()
            state = InvestmentState(points=points, fetched_at=datetime.now(), loading=False)
            self._save_cache(state)
        except (OSError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
            cached_points = self.snapshot().points
            state = InvestmentState(points=cached_points, error="SIN DATOS", loading=False)

        with self._lock:
            self.state = state

    def _fetch_points(self):
        start = date.fromisoformat(self.config["investment_start_date"])
        period1 = int(datetime.combine(start, time.min, tzinfo=timezone.utc).timestamp())
        period2 = int(datetime.now(timezone.utc).timestamp())

        symbol = self.config["investment_symbol"]
        params = {
            "period1": period1,
            "period2": period2,
            "interval": "1d",
            "events": "history",
            "includeAdjustedClose": "true",
        }
        url = (
            "https://query1.finance.yahoo.com/v8/finance/chart/"
            + urllib.parse.quote(symbol)
            + "?"
            + urllib.parse.urlencode(params)
        )

        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen_with_cert_fallback(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))

        result = payload["chart"]["result"][0]
        timestamps = result["timestamp"]
        quote = result["indicators"]["quote"][0]
        adjclose = result["indicators"].get("adjclose", [{}])[0].get("adjclose", [])
        closes = adjclose or quote["close"]

        points = []
        for ts, close in zip(timestamps, closes):
            if close is None:
                continue
            points.append(
                InvestmentPoint(
                    datetime.fromtimestamp(ts, tz=timezone.utc).date(),
                    float(close),
                )
            )

        if not points:
            raise ValueError("No investment points returned")

        return points
