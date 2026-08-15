from serpapi_challenge26.caching import CacheMiss, CachedResponse, CachingClient


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
