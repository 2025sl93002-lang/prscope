"""Tests for safe git invocation & path/ref validation. SPDX-License-Identifier: MIT"""
import pytest

from prscope.services.gitutil import GitError, is_git_repo, validate_ref


@pytest.mark.parametrize("ref", ["main", "feature/x", "v1.2.3", "a1b2c3d", "HEAD", "release-1.0"])
def test_valid_refs(ref):
    assert validate_ref(ref) == ref


@pytest.mark.parametrize("ref", [
    "", "-x", "--upload-pack=evil", "a b", "foo;rm -rf", "a..b", "a//b",
    "x$(whoami)", "`id`", "a\nb", "branch.lock",
])
def test_invalid_refs_rejected(ref):
    with pytest.raises(GitError):
        validate_ref(ref)


def test_is_git_repo_true_for_demo(demo_repo):
    assert is_git_repo(demo_repo) is True


def test_is_git_repo_false_for_tmp(tmp_path):
    assert is_git_repo(tmp_path) is False


def test_safe_repo_path_rejects_missing(tmp_path):
    from prscope.services.gitutil import safe_repo_path
    with pytest.raises(GitError):
        safe_repo_path(str(tmp_path / "does-not-exist"))
