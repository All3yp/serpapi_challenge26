"""HTTP cache over the SerpApi SDK, keyed by request parameters."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import serpapi

_DIGEST_LENGTH = 16
_API_KEY_PARAM = "api_key"
_ENGINE_FALLBACK = "google"


class CachedResponse:
    """Minimal ``requests.Response`` stand-in for replayed JSON."""

    def __init__(self, data: dict) -> None:
        self._data = data

    def json(self) -> dict:
        return self._data

    @property
    def text(self) -> str:
        return json.dumps(self._data)

    def raise_for_status(self) -> None:
        return None


class CacheMiss(RuntimeError):
    """A ``replay`` request has no recorded fixture."""


class CachingClient(serpapi.Client):
    """SerpApi client that caches responses to disk in record/replay modes."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        timeout: float | None = None,
        cache_dir: str | Path = "fixtures",
        mode: str = "replay",
    ) -> None:
        super().__init__(api_key=api_key, timeout=timeout)
        self.cache_dir = Path(cache_dir)
        self.mode = mode
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_key(self, method: str, path: str, params: dict | None) -> str:
        normalized = {
            key: value
            for key, value in sorted((params or {}).items())
            if key != _API_KEY_PARAM
        }
        engine = normalized.get("engine", _ENGINE_FALLBACK)
        canonical = json.dumps(
            {"method": method, "path": path, "params": normalized},
            sort_keys=True,
            default=str,
        )
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:_DIGEST_LENGTH]
        return f"{engine}_{digest}.json"

    def _cache_path(self, method: str, path: str, params: dict | None) -> Path:
        return self.cache_dir / self._cache_key(method, path, params)

    @staticmethod
    def _load(path: Path) -> CachedResponse:
        return CachedResponse(json.loads(path.read_text(encoding="utf-8")))

    @staticmethod
    def _save(path: Path, response) -> None:
        try:
            data = response.json()
        except (ValueError, AttributeError):
            return
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def request(self, method, path, params, *, assert_200=True, **kwargs):
        cache_path = self._cache_path(method, path, params)

        if self.mode in ("record", "replay") and cache_path.exists():
            return self._load(cache_path)

        if self.mode == "replay":
            raise CacheMiss(
                f"No cached fixture for {self._cache_key(method, path, params)}. "
                "Switch mode to 'record' or 'online' to fetch it once."
            )

        response = super().request(method, path, params, assert_200=assert_200, **kwargs)
        if self.mode == "record":
            self._save(cache_path, response)
        return response
