"""Tests for the deterministic change classifier. SPDX-License-Identifier: MIT"""
import pytest

from prscope.models import FileCategory
from prscope.services.classifier import classify_path


@pytest.mark.parametrize("path,category", [
    ("src/app/service.py", FileCategory.source),
    ("src/components/Button.tsx", FileCategory.ui),
    ("tests/test_service.py", FileCategory.test),
    ("src/__tests__/foo.test.ts", FileCategory.test),
    ("requirements.txt", FileCategory.dependency),
    ("package.json", FileCategory.dependency),
    ("Dockerfile", FileCategory.infrastructure),
    (".github/workflows/ci.yml", FileCategory.build_ci),
    ("migrations/0001_init.sql", FileCategory.migration),
    ("api/openapi.yaml", FileCategory.api_contract),
    ("src/auth/login.py", FileCategory.security),
    ("docs/guide.md", FileCategory.documentation),
    ("config/app.ini", FileCategory.config),
    ("assets/logo.bin", FileCategory.unknown),
])
def test_classification(path, category):
    result = classify_path(path)
    assert result.category == category
    assert result.matched_rule
    assert result.reason


def test_every_classification_is_explainable():
    r = classify_path("src/payment/payment_service.py")
    assert r.confidence > 0
    assert "source" in r.category.value


def test_security_beats_source():
    # An auth source file should classify as security, not plain source.
    assert classify_path("src/security/jwt.py").category == FileCategory.security


def test_test_beats_source():
    assert classify_path("tests/test_payment.py").category == FileCategory.test
