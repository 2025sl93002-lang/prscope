"""Demo repository builder — the "Payment Processing Refactor" scenario.

Creates a **real** local git repository with a ``main`` and a ``feature`` branch
so the demo runs through the actual analysis engine (no hardcoded results). The
feature branch demonstrates: a modified payment module, a new module with a
missing test, a changed API contract, a configuration change, a dependency
change, and real dependency impact. SPDX-License-Identifier: MIT
"""
from __future__ import annotations

from pathlib import Path

from .gitutil import GitError, is_git_repo, run_git

# --------------------------------------------------------------------------- #
# File contents — base (main branch)
# --------------------------------------------------------------------------- #

_BASE = {
    "src/payment/payment_service.py": '''\
"""Payment service — base implementation."""


class PaymentService:
    def __init__(self, gateway):
        self.gateway = gateway

    def charge(self, amount, currency="USD"):
        if amount <= 0:
            raise ValueError("amount must be positive")
        return self.gateway.submit({"amount": amount, "currency": currency})
''',
    "src/payment/checkout_controller.py": '''\
"""Checkout controller depends on the payment service."""
from src.payment.payment_service import PaymentService


class CheckoutController:
    def __init__(self, gateway):
        self.service = PaymentService(gateway)

    def checkout(self, cart):
        return self.service.charge(cart["total"], cart.get("currency", "USD"))
''',
    "src/payment/order_processor.py": '''\
"""Order processor also depends on the payment service."""
from src.payment.payment_service import PaymentService


class OrderProcessor:
    def __init__(self, gateway):
        self.service = PaymentService(gateway)

    def process(self, order):
        return self.service.charge(order["amount"])
''',
    "tests/test_payment_service.py": '''\
"""Happy-path tests for PaymentService."""
from src.payment.payment_service import PaymentService


class FakeGateway:
    def submit(self, payload):
        return {"ok": True, **payload}


def test_charge_valid():
    svc = PaymentService(FakeGateway())
    assert svc.charge(100)["ok"] is True
''',
    "api/openapi.yaml": '''\
openapi: 3.0.0
info:
  title: Payment API
  version: 1.0.0
paths:
  /charge:
    post:
      summary: Charge a payment
      responses:
        "200":
          description: Charged
''',
    "config/app.yaml": '''\
payment:
  default_currency: USD
  retry_attempts: 1
''',
    "requirements.txt": "requests==2.31.0\n",
    "README.md": "# Demo Shop\n\nSample repository for the PRScope demo.\n",
}

# --------------------------------------------------------------------------- #
# File contents — feature branch (the refactor)
# --------------------------------------------------------------------------- #

_FEATURE_CHANGES = {
    # Significant refactor of the payment module.
    "src/payment/payment_service.py": '''\
"""Payment service — refactored with retry and currency validation."""

SUPPORTED_CURRENCIES = {"USD", "EUR", "GBP"}


class PaymentService:
    def __init__(self, gateway, retry_attempts=1):
        self.gateway = gateway
        self.retry_attempts = retry_attempts

    def charge(self, amount, currency="USD"):
        if amount <= 0:
            raise ValueError("amount must be positive")
        if currency not in SUPPORTED_CURRENCIES:
            raise ValueError(f"unsupported currency: {currency}")
        last_error = None
        for _ in range(max(1, self.retry_attempts)):
            try:
                return self.gateway.submit({"amount": amount, "currency": currency})
            except Exception as exc:  # retry on gateway failure
                last_error = exc
        raise RuntimeError(f"charge failed after retries: {last_error}")
''',
    # New module with NO corresponding test -> potential test gap.
    "src/payment/refund_service.py": '''\
"""Refund service — new module (note: no dedicated test yet)."""
from src.payment.payment_service import SUPPORTED_CURRENCIES


class RefundService:
    def __init__(self, gateway):
        self.gateway = gateway

    def refund(self, amount, currency="USD"):
        if currency not in SUPPORTED_CURRENCIES:
            raise ValueError(f"unsupported currency: {currency}")
        return self.gateway.refund({"amount": amount, "currency": currency})
''',
    # Checkout now also depends on the new refund service -> dependency impact.
    "src/payment/checkout_controller.py": '''\
"""Checkout controller now supports refunds via the new service."""
from src.payment.payment_service import PaymentService
from src.payment.refund_service import RefundService


class CheckoutController:
    def __init__(self, gateway):
        self.service = PaymentService(gateway, retry_attempts=2)
        self.refunds = RefundService(gateway)

    def checkout(self, cart):
        return self.service.charge(cart["total"], cart.get("currency", "USD"))

    def refund(self, cart):
        return self.refunds.refund(cart["total"], cart.get("currency", "USD"))
''',
    # API contract change.
    "api/openapi.yaml": '''\
openapi: 3.0.0
info:
  title: Payment API
  version: 1.1.0
paths:
  /charge:
    post:
      summary: Charge a payment
      responses:
        "200":
          description: Charged
  /refund:
    post:
      summary: Refund a payment
      responses:
        "200":
          description: Refunded
''',
    # Configuration change.
    "config/app.yaml": '''\
payment:
  default_currency: USD
  retry_attempts: 2
  supported_currencies: [USD, EUR, GBP]
''',
    # Dependency change.
    "requirements.txt": "requests==2.32.3\ntenacity==9.0.0\n",
    # Test modified (happy path updated) but failure/negative case still missing.
    "tests/test_payment_service.py": '''\
"""Happy-path tests for PaymentService (negative cases still missing)."""
from src.payment.payment_service import PaymentService


class FakeGateway:
    def submit(self, payload):
        return {"ok": True, **payload}


def test_charge_valid():
    svc = PaymentService(FakeGateway())
    assert svc.charge(100, "EUR")["ok"] is True
''',
}


def _write_files(root: Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def build_demo_repo(dest: Path, *, force: bool = False) -> Path:
    """Create (idempotently) the demo git repository and return its path."""
    dest = dest.resolve()
    if dest.exists() and is_git_repo(dest) and not force:
        return dest
    if force and dest.exists():
        import shutil

        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)

    run_git(dest, ["init", "-q", "-b", "main"])
    run_git(dest, ["config", "user.email", "demo@prscope.local"])
    run_git(dest, ["config", "user.name", "PRScope Demo"])
    run_git(dest, ["config", "commit.gpgsign", "false"])

    _write_files(dest, _BASE)
    run_git(dest, ["add", "-A"])
    run_git(dest, ["commit", "-q", "-m", "Initial demo shop"])

    run_git(dest, ["checkout", "-q", "-b", "feature/payment-refactor"])
    _write_files(dest, _FEATURE_CHANGES)
    run_git(dest, ["add", "-A"])
    run_git(
        dest,
        ["commit", "-q", "-m",
         "Payment processing refactor: retries, refunds, currency validation"],
    )

    run_git(dest, ["checkout", "-q", "main"])
    if not is_git_repo(dest):  # pragma: no cover
        raise GitError("Failed to initialize demo repository.")
    return dest
