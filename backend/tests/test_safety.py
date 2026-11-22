import os

import pytest

from deplens.services.safety import (
    PathSafetyError,
    is_within,
    iter_source_files,
    read_text_capped,
    resolve_project_root,
)


def test_resolve_rejects_missing_path():
    with pytest.raises(PathSafetyError):
        resolve_project_root("/definitely/not/here/xyz123")


def test_resolve_accepts_dir(tmp_path):
    assert resolve_project_root(str(tmp_path)) == tmp_path.resolve()


def test_is_within(tmp_path):
    inside = tmp_path / "sub" / "file.js"
    inside.parent.mkdir()
    inside.write_text("x")
    assert is_within(tmp_path, inside)
    assert not is_within(tmp_path, tmp_path.parent / "outside.js")


def test_iter_skips_node_modules_and_symlinks(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.js").write_text("x")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "b.js").write_text("x")
    found = {p.name for p in iter_source_files(tmp_path, {".js"})}
    assert "a.js" in found
    assert "b.js" not in found  # node_modules pruned


def test_iter_does_not_follow_symlinked_dirs(tmp_path):
    (tmp_path / "real").mkdir()
    (tmp_path / "real" / "r.js").write_text("x")
    secret = tmp_path.parent / "secret_dir_xyz"
    secret.mkdir(exist_ok=True)
    (secret / "leak.js").write_text("secret")
    link = tmp_path / "link"
    try:
        os.symlink(secret, link)
    except OSError:
        pytest.skip("symlinks not supported")
    found = {p.name for p in iter_source_files(tmp_path, {".js"})}
    assert "r.js" in found
    assert "leak.js" not in found  # symlinked dir not traversed
    secret_file = secret / "leak.js"
    secret_file.unlink()
    secret.rmdir()


def test_read_text_capped(tmp_path):
    f = tmp_path / "big.js"
    f.write_text("a" * 100)
    assert len(read_text_capped(f, cap=10)) == 10
