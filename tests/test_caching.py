import pytest
import serpapi

from gap_finder.caching import CacheMiss, CachedResponse, CachingClient


def test_cache_key_excludes_api_key(tmp_path):
    params = {"engine": "google_scholar", "q": "x", "api_key": "key-a"}
    first = CachingClient(api_key="key-a", mode="replay", cache_dir=tmp_path)
    second = CachingClient(api_key="key-b", mode="replay", cache_dir=tmp_path)
    assert first._cache_key("GET", "/search", params) == second._cache_key("GET", "/search", params)


def test_replay_misses_raise_cache_miss(tmp_path):
    client = CachingClient(api_key=None, mode="replay", cache_dir=tmp_path)
    try:
        client.request("GET", "/search", {"engine": "google_scholar", "q": "missing"})
    except CacheMiss:
        return
    raise AssertionError("CacheMiss not raised")


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "x.json"
    CachingClient._save(path, CachedResponse({"a": 1}))
    assert CachingClient._load(path).json() == {"a": 1}


def test_invalid_mode_raises(tmp_path):
    with pytest.raises(ValueError):
        CachingClient(api_key=None, mode="foo", cache_dir=tmp_path)


def test_valid_initialized(tmp_path):
    cache_dir = tmp_path / "fixtures"
    client = CachingClient(
        api_key="secret-key",
        timeout=12.5,
        cache_dir=cache_dir,
        mode="record",
    )
    # SerpApi base-class state propagated through super().__init__.
    assert client.api_key == "secret-key"
    assert client.timeout == 12.5
    assert client.session is not None
    # CachingClient's own state.
    assert client.mode == "record"
    assert client.cache_dir == cache_dir
    assert cache_dir.is_dir()


def test_cache_key_stable_across_parameter_order(tmp_path):
    first = CachingClient(mode="replay", cache_dir=tmp_path)
    second = CachingClient(mode="replay", cache_dir=tmp_path)
    key_a = first._cache_key("GET", "/search", {"engine": "google_scholar", "q": "x", "num": 20})
    key_b = second._cache_key("GET", "/search", {"num": 20, "q": "x", "engine": "google_scholar"})
    assert key_a == key_b


def test_cache_key_changes_with_query(tmp_path):
    client = CachingClient(mode="replay", cache_dir=tmp_path)
    key_a = client._cache_key("GET", "/search", {"engine": "google_scholar", "q": "alpha"})
    key_b = client._cache_key("GET", "/search", {"engine": "google_scholar", "q": "beta"})
    assert key_a != key_b


def test_cache_key_changes_with_start_offset(tmp_path):
    client = CachingClient(mode="replay", cache_dir=tmp_path)
    base = {"engine": "google_scholar", "q": "x"}
    key_page1 = client._cache_key("GET", "/search", {**base, "start": 0})
    key_page2 = client._cache_key("GET", "/search", {**base, "start": 20})
    assert key_page1 != key_page2


def test_replay_returns_cached_response_without_network(tmp_path, monkeypatch):
    client = CachingClient(api_key="key-a", mode="replay", cache_dir=tmp_path)

    def _fail(*args, **kwargs):
        raise AssertionError("replay must not hit the network")

    # Pre-seed a fixture file directly, then confirm replay serves it.
    params = {"engine": "google_scholar", "q": "cached"}
    path = client._cache_path("GET", "/search", params)
    CachingClient._save(path, CachedResponse({"organic_results": [{"title": "hit"}]}))

    monkeypatch.setattr(serpapi.Client, "request", _fail)
    response = client.request("GET", "/search", params)
    assert response.json()["organic_results"][0]["title"] == "hit"


def test_online_mode_writes_nothing_and_returns_response(tmp_path, monkeypatch):
    client = CachingClient(api_key="key-a", mode="online", cache_dir=tmp_path)

    def _fake_request(self, method, path, params, assert_200=True, **kwargs):
        return CachedResponse({"engine": params.get("engine")})

    monkeypatch.setattr(serpapi.Client, "request", _fake_request)
    response = client.request("GET", "/search", {"engine": "google_scholar", "q": "live"})
    assert response.json() == {"engine": "google_scholar"}
    assert list(tmp_path.iterdir()) == []


def test_record_mode_saves_response_to_disk(tmp_path, monkeypatch):
    client = CachingClient(api_key="key-a", mode="record", cache_dir=tmp_path)

    def _fake_request(self, method, path, params, assert_200=True, **kwargs):
        return CachedResponse({"organic_results": [{"title": "fresh"}]})

    monkeypatch.setattr(serpapi.Client, "request", _fake_request)
    params = {"engine": "google_scholar", "q": "fresh"}
    response = client.request("GET", "/search", params)
    assert response.json()["organic_results"][0]["title"] == "fresh"

    path = client._cache_path("GET", "/search", params)
    assert path.exists()
    assert CachingClient._load(path).json()["organic_results"][0]["title"] == "fresh"


def test_record_mode_serves_existing_fixture_without_network(tmp_path, monkeypatch):
    client = CachingClient(api_key="key-a", mode="record", cache_dir=tmp_path)
    params = {"engine": "google_scholar", "q": "existing"}
    path = client._cache_path("GET", "/search", params)
    CachingClient._save(path, CachedResponse({"organic_results": [{"title": "stale"}]}))

    def _fail(*args, **kwargs):
        raise AssertionError("existing fixture must be served, not refetched")

    monkeypatch.setattr(serpapi.Client, "request", _fail)
    response = client.request("GET", "/search", params)
    assert response.json()["organic_results"][0]["title"] == "stale"


def test_cache_key_engine_is_embedded_in_filename(tmp_path):
    client = CachingClient(mode="replay", cache_dir=tmp_path)
    key = client._cache_key("GET", "/search", {"engine": "google_scholar", "q": "x"})
    assert key.startswith("google_scholar_")
    assert key.endswith(".json")


def test_save_ignores_non_json_response(tmp_path):
    class NonJson:
        def json(self):
            raise ValueError("not json")

    path = tmp_path / "bad.json"
    CachingClient._save(path, NonJson())
    assert not path.exists()


def test_save_ignores_response_without_json_method(tmp_path):
    class NoJson:
        pass

    path = tmp_path / "bad.json"
    CachingClient._save(path, NoJson())
    assert not path.exists()


def test_cached_response_text_is_json():
    assert CachedResponse({"a": 1}).text == '{"a": 1}'


def test_cached_response_raise_for_status_is_noop():
    CachedResponse({"a": 1}).raise_for_status()  # must not raise


def test_cache_dir_is_created_on_init(tmp_path):
    cache_dir = tmp_path / "nested" / "fixtures"
    CachingClient(mode="replay", cache_dir=cache_dir)
    assert cache_dir.is_dir()
