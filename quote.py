"""Frase del Dia API client."""

import json
import ssl
import threading
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.error import URLError


CACHE_DIR = Path(__file__).with_name(".cache")


@dataclass
class QuoteState:
    phrase: str | None = None
    author: str | None = None
    fetched_at: datetime | None = None
    error: str | None = None
    loading: bool = False


def urlopen_with_cert_fallback(url, timeout):
    try:
        return urllib.request.urlopen(url, timeout=timeout)
    except URLError as exc:
        if not isinstance(exc.reason, ssl.SSLCertVerificationError):
            raise

        context = ssl._create_unverified_context()
        return urllib.request.urlopen(url, timeout=timeout, context=context)


class QuoteClient:
    def __init__(self, config):
        self.config = config
        self.state = QuoteState()
        self._elapsed = float(config["quote_refresh_seconds"])
        self._thread = None
        self._lock = threading.Lock()
        self._load_cache()

    def update(self, dt):
        self._elapsed += dt
        if self._elapsed >= self.config["quote_refresh_seconds"]:
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
            return QuoteState(
                phrase=self.state.phrase,
                author=self.state.author,
                fetched_at=self.state.fetched_at,
                error=self.state.error,
                loading=self.state.loading,
            )

    def _cache_path(self):
        return CACHE_DIR / "quote.json"

    def _load_cache(self):
        path = self._cache_path()
        if not path.exists():
            return

        try:
            with path.open("r", encoding="utf-8") as fh:
                payload = json.load(fh)
            fetched_at = datetime.fromisoformat(payload["fetched_at"]) if payload.get("fetched_at") else None
            self.state = QuoteState(
                phrase=payload.get("phrase"),
                author=payload.get("author"),
                fetched_at=fetched_at,
            )
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            return

    def _save_cache(self, state):
        CACHE_DIR.mkdir(exist_ok=True)
        payload = {
            "phrase": state.phrase,
            "author": state.author,
            "fetched_at": state.fetched_at.isoformat() if state.fetched_at else None,
        }

        with self._cache_path().open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
            fh.write("\n")

    def _fetch(self):
        try:
            with urlopen_with_cert_fallback(self.config["quote_url"], timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))

            state = QuoteState(
                phrase=str(payload["phrase"]).strip(),
                author=str(payload["author"]).strip(),
                fetched_at=datetime.now(),
                loading=False,
            )
            self._save_cache(state)
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            cached = self.snapshot()
            state = QuoteState(
                phrase=cached.phrase,
                author=cached.author,
                fetched_at=cached.fetched_at,
                error="SIN DATOS",
                loading=False,
            )

        with self._lock:
            self.state = state
