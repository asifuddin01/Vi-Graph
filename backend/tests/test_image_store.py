import hashlib
from pathlib import Path

import pytest

from app.storage.images import ImageStore

DATA = b"fake image bytes"
SHA = hashlib.sha256(DATA).hexdigest()


@pytest.fixture
def store(tmp_path: Path) -> ImageStore:
    return ImageStore(tmp_path / "images")


@pytest.mark.parametrize(("fmt", "ext"), [("PNG", "png"), ("JPEG", "jpg"), ("WEBP", "webp")])
def test_files_are_named_by_hash_and_detected_format(store: ImageStore, fmt: str, ext: str) -> None:
    path = store.save(DATA, SHA, fmt)

    assert path == store.root / f"{SHA}.{ext}"
    assert path.read_bytes() == DATA


def test_load_round_trips_and_missing_is_none(store: ImageStore) -> None:
    store.save(DATA, SHA, "PNG")

    assert store.load(SHA, "PNG") == DATA
    assert store.load(SHA, "JPEG") is None


def test_saving_twice_keeps_one_file_and_no_temp_files(store: ImageStore) -> None:
    store.save(DATA, SHA, "PNG")
    store.save(DATA, SHA, "PNG")

    assert [p.name for p in store.root.iterdir()] == [f"{SHA}.png"]


@pytest.mark.parametrize("sha", ["../../etc/passwd", "ABC", SHA.upper(), SHA + "0"])
def test_non_hash_names_are_rejected(store: ImageStore, sha: str) -> None:
    with pytest.raises(ValueError, match="sha256"):
        store.path_for(sha, "PNG")


def test_unsupported_format_is_rejected(store: ImageStore) -> None:
    with pytest.raises(ValueError, match="unsupported image format"):
        store.path_for(SHA, "GIF")
