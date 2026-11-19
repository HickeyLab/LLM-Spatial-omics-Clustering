"""Small deterministic helpers; never inspect credentials or call a provider."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024**2), b""):
            h.update(block)
    return h.hexdigest()


def strict_json(text):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError(f"Duplicate JSON key: {key}")
            out[key] = value
        return out
    return json.loads(text, object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def read_json(path):
    return strict_json(Path(path).read_text())


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def new_output(path):
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"Preserve existing output; choose a new destination: {path}")
    path.mkdir(parents=True)
    return path


def verify_index(root, index, names=None):
    """Reject path escapes and changed indexed evidence before consuming it."""
    root = Path(root).resolve()
    for name in index if names is None else names:
        if name not in index:
            raise ValueError(f"Unindexed source: {name}")
        path = (root / name).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Indexed path escapes its artifact root")
        expected = index[name]
        expected = expected["sha256"] if isinstance(expected, dict) else expected
        if file_sha(path) != expected:
            raise ValueError(f"Indexed file changed: {name}")
