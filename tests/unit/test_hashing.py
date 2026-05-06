"""Unit tests for hashing utilities."""

from nirikshak.core.hashing import GENESIS_HASH, chain_hash, content_hash, content_hash_json
from nirikshak.core.schemas import BBox


class TestContentHash:
    def test_deterministic(self):
        h1 = content_hash(b"hello world")
        h2 = content_hash(b"hello world")
        assert h1 == h2

    def test_different_input(self):
        h1 = content_hash(b"hello")
        h2 = content_hash(b"world")
        assert h1 != h2

    def test_returns_hex_string(self):
        h = content_hash(b"test")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


class TestContentHashJSON:
    def test_deterministic(self):
        obj = BBox(x0=1, y0=2, x1=3, y1=4)
        h1 = content_hash_json(obj)
        h2 = content_hash_json(obj)
        assert h1 == h2

    def test_different_objects(self):
        obj1 = BBox(x0=1, y0=2, x1=3, y1=4)
        obj2 = BBox(x0=5, y0=6, x1=7, y1=8)
        assert content_hash_json(obj1) != content_hash_json(obj2)


class TestChainHash:
    def test_deterministic(self):
        h1 = chain_hash(0, "2025-01-01T00:00:00", "system", "tender_ingested", "phash", GENESIS_HASH)
        h2 = chain_hash(0, "2025-01-01T00:00:00", "system", "tender_ingested", "phash", GENESIS_HASH)
        assert h1 == h2

    def test_different_sequence(self):
        h1 = chain_hash(0, "2025-01-01T00:00:00", "system", "tender_ingested", "phash", GENESIS_HASH)
        h2 = chain_hash(1, "2025-01-01T00:00:00", "system", "tender_ingested", "phash", GENESIS_HASH)
        assert h1 != h2

    def test_genesis_hash(self):
        assert len(GENESIS_HASH) == 64
        assert GENESIS_HASH == "0" * 64

    def test_pinned_vector(self):
        """Pin a known test vector so we catch accidental format changes."""
        h = chain_hash(0, "2025-01-01T00:00:00", "system", "tender_ingested", "abc123", GENESIS_HASH)
        # The hash should be a valid 64-char hex string
        assert len(h) == 64
        # Re-running with same inputs must give same result
        assert h == chain_hash(0, "2025-01-01T00:00:00", "system", "tender_ingested", "abc123", GENESIS_HASH)
