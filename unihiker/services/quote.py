"""Daily fact API client."""

import json
import ssl
import threading
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from urllib.error import URLError

from unihiker.paths import CACHE_DIR


@dataclass
class QuoteState:
    phrase: str | None = None
    source: str | None = None
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
        self._last_scheduled_attempt_date = None
        self._thread = None
        self._lock = threading.Lock()
        self._load_cache()

    def update(self, dt):
        now = datetime.now()
        if (
            now.hour == self.config["quote_refresh_hour"]
            and self._last_scheduled_attempt_date != now.date()
        ):
            self._last_scheduled_attempt_date = now.date()
            self.fetch_async()

    def fetch_async(self):
        if self._thread and self._thread.is_alive():
            return

        with self._lock:
            self.state.loading = True
            self.state.error = None

        self._thread = threading.Thread(target=self._fetch, daemon=True)
        self._thread.start()

    def reset_schedule(self):
        self._last_scheduled_attempt_date = None

    def snapshot(self):
        with self._lock:
            return QuoteState(
                phrase=self.state.phrase,
                source=self.state.source,
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
                phrase=payload.get("text", payload.get("phrase")),
                source=payload.get("source"),
                fetched_at=fetched_at,
            )
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            return

    def _save_cache(self, state):
        CACHE_DIR.mkdir(exist_ok=True)
        payload = {
            "text": state.phrase,
            "source": state.source,
            "fetched_at": state.fetched_at.isoformat() if state.fetched_at else None,
        }

        with self._cache_path().open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
            fh.write("\n")

    def _fetch(self):
        try:
            with urlopen_with_cert_fallback(self.config["quote_url"], timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))

            text = payload.get("text")
            if text is None:
                raise ValueError("missing quote text")
            state = QuoteState(
                phrase=str(text).strip(),
                source=str(payload.get("source") or "").strip() or None,
                fetched_at=datetime.now(),
                loading=False,
            )
            if not state.phrase:
                raise ValueError("empty quote text")
            self._save_cache(state)
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            cached = self.snapshot()
            state = QuoteState(
                phrase=cached.phrase,
                source=cached.source,
                fetched_at=cached.fetched_at,
                error="SIN DATOS",
                loading=False,
            )

        with self._lock:
            self.state = state
