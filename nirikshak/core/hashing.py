"""SHA-256 hashing utilities for content integrity and audit chain."""

import hashlib
import json

from pydantic import BaseModel

GENESIS_HASH = "0" * 64


def content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def content_hash_json(obj: BaseModel) -> str:
    raw = json.dumps(obj.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def chain_hash(
    sequence: int,
    timestamp: str,
    actor: str,
    action_type: str,
    payload_hash: str,
    previous_hash: str,
) -> str:
    combined = f"{sequence}|{timestamp}|{actor}|{action_type}|{payload_hash}|{previous_hash}"
    return hashlib.sha256(combined.encode()).hexdigest()
