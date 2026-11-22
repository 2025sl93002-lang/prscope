from deplens import semver


class TestParse:
    def test_basic(self):
        v = semver.parse("1.2.3")
        assert (v.major, v.minor, v.patch) == (1, 2, 3)
        assert not v.is_prerelease

    def test_prerelease_and_build(self):
        v = semver.parse("2.0.0-beta.1+build.5")
        assert v.is_prerelease
        assert v.prerelease == ("beta", "1")
        assert str(v) == "2.0.0-beta.1"

    def test_v_prefix(self):
        assert str(semver.parse("v1.0.0")) == "1.0.0"

    def test_invalid(self):
        import pytest

        for bad in ["", "1", "1.2", "abc", "1.2.x", "1.2.3.4"]:
            with pytest.raises(semver.InvalidVersion):
                semver.parse(bad)

    def test_clean(self):
        assert semver.clean("v1.2.3") == "1.2.3"
        assert semver.clean("not-a-version") is None


class TestCompare:
    def test_ordering(self):
        assert semver.compare("1.0.0", "2.0.0") == -1
        assert semver.compare("2.0.0", "1.0.0") == 1
        assert semver.compare("1.2.3", "1.2.3") == 0

    def test_prerelease_precedence(self):
        # Per semver spec: prerelease < release.
        assert semver.compare("1.0.0-alpha", "1.0.0") == -1
        assert semver.compare("1.0.0-alpha", "1.0.0-alpha.1") == -1
        assert semver.compare("1.0.0-alpha.1", "1.0.0-beta") == -1
        assert semver.compare("1.0.0-beta.2", "1.0.0-beta.11") == -1  # numeric id


class TestDiff:
    def test_classification(self):
        assert semver.diff("1.2.3", "2.0.0") == "major"
        assert semver.diff("1.2.3", "1.3.0") == "minor"
        assert semver.diff("1.2.3", "1.2.4") == "patch"
        assert semver.diff("1.2.3", "1.2.3") is None
        assert semver.diff("1.0.0-a", "1.0.0-b") == "prerelease"

    def test_order_independent(self):
        assert semver.diff("2.0.0", "1.2.3") == "major"


class TestSatisfies:
    def test_caret(self):
        assert semver.satisfies("1.2.3", "^1.0.0")
        assert not semver.satisfies("2.0.0", "^1.0.0")
        assert semver.satisfies("0.2.5", "^0.2.3")
        assert not semver.satisfies("0.3.0", "^0.2.3")  # caret pins minor when major is 0

    def test_tilde(self):
        assert semver.satisfies("1.2.9", "~1.2.0")
        assert not semver.satisfies("1.3.0", "~1.2.0")

    def test_x_ranges(self):
        assert semver.satisfies("1.5.0", "1.x")
        assert not semver.satisfies("2.0.0", "1.x")
        assert semver.satisfies("1.2.9", "1.2.x")

    def test_comparators(self):
        assert semver.satisfies("1.5.0", ">=1.0.0 <2.0.0")
        assert not semver.satisfies("2.0.0", ">=1.0.0 <2.0.0")
        assert semver.satisfies("1.5.0", "<2")
        assert not semver.satisfies("1.0.0", ">1")

    def test_or_and_hyphen(self):
        assert semver.satisfies("2.1.0", "1.0.0 || >=2.0.0")
        assert not semver.satisfies("1.2.3", "1.0.0 || >=2.0.0")
        assert semver.satisfies("1.5.0", "1.2.3 - 2.0.0")

    def test_wildcard_and_tags(self):
        assert semver.satisfies("1.2.3", "*")
        assert semver.satisfies("1.2.3", "")
        assert semver.satisfies("1.2.3", "latest")

    def test_prerelease_only_in_matching_range(self):
        assert not semver.satisfies("1.0.0-beta", "^1.0.0")
        assert semver.satisfies("1.0.0-beta.2", ">=1.0.0-beta.1 <2")

    def test_non_semver_specs(self):
        # git/url/file specs are treated as "any resolved version is fine".
        assert semver.satisfies("1.0.0", "github:user/repo")
        assert semver.satisfies("1.0.0", "file:../local")

    def test_invalid_version_never_satisfies(self):
        assert not semver.satisfies("not-a-version", "^1.0.0")


class TestMaxSatisfying:
    def test_picks_highest(self):
        versions = ["1.0.0", "1.2.0", "1.9.9", "2.0.0"]
        assert semver.max_satisfying(versions, "^1.0.0") == "1.9.9"
        assert semver.max_satisfying(versions, "*") == "2.0.0"
        assert semver.max_satisfying(versions, "^3.0.0") is None
