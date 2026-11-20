"""Tests for the verification planner. SPDX-License-Identifier: MIT"""
from prscope.services import verification_planner as vp


def test_source_change_generates_unit_test_task():
    tasks = vp.plan_verification([
        {"path": "a.py", "category": "source", "change_type": "modified",
         "lines_added": 5, "lines_removed": 1},
    ])
    keys = {t.task_key for t in tasks}
    assert "source:unit-tests" in keys
    assert "source:regression" in keys


def test_api_and_migration_tasks():
    tasks = vp.plan_verification([
        {"path": "api.yaml", "category": "api_contract", "change_type": "modified",
         "lines_added": 1, "lines_removed": 0},
        {"path": "m.sql", "category": "migration", "change_type": "added",
         "lines_added": 10, "lines_removed": 0},
    ])
    keys = {t.task_key for t in tasks}
    assert "api:compatibility" in keys
    assert "migration:validate" in keys


def test_tasks_have_required_fields():
    tasks = vp.plan_verification([
        {"path": "auth.py", "category": "security", "change_type": "modified",
         "lines_added": 2, "lines_removed": 0},
    ])
    assert tasks
    for t in tasks:
        assert t.title and t.description and t.reason
        assert t.steps and t.evidence_requirements
        assert t.verification_type


def test_deterministic_keys_stable():
    cf = [{"path": "a.py", "category": "source", "change_type": "modified",
           "lines_added": 1, "lines_removed": 0}]
    a = [t.task_key for t in vp.plan_verification(cf)]
    b = [t.task_key for t in vp.plan_verification(cf)]
    assert a == b
