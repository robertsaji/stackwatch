"""Tests for stackwatch.budget."""
from __future__ import annotations

import pytest

from stackwatch.budget import (
    BudgetConfig,
    BudgetError,
    BudgetResult,
    check_budget,
    render_budget_text,
)
from stackwatch.drift import DriftResult, DriftedResource


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(stack: str, drifted_count: int) -> DriftResult:
    resources = [
        DriftedResource(
            logical_id=f"Res{i}",
            resource_type="AWS::S3::Bucket",
            drift_status="MODIFIED",
            expected_properties="{}",
            actual_properties="{\"X\":1}",
        )
        for i in range(drifted_count)
    ]
    return DriftResult(
        stack_name=stack,
        drift_status="DRIFTED" if drifted_count else "IN_SYNC",
        drifted_resources=resources,
    )


# ---------------------------------------------------------------------------
# BudgetConfig validation
# ---------------------------------------------------------------------------

def test_invalid_cost_per_resource_raises():
    with pytest.raises(BudgetError):
        BudgetConfig(cost_per_drifted_resource=-1.0)


def test_invalid_monthly_budget_raises():
    with pytest.raises(BudgetError):
        BudgetConfig(monthly_budget=0)


def test_invalid_warn_threshold_raises():
    with pytest.raises(BudgetError):
        BudgetConfig(warn_threshold=0.0)


def test_warn_threshold_above_one_raises():
    with pytest.raises(BudgetError):
        BudgetConfig(warn_threshold=1.5)


# ---------------------------------------------------------------------------
# check_budget logic
# ---------------------------------------------------------------------------

def test_no_drift_zero_cost():
    results = [_make_result("stack-a", 0)]
    out = check_budget(results)
    assert out.estimated_cost == 0.0
    assert not out.over_budget
    assert not out.near_budget
    assert out.drifted_resource_count == 0


def test_estimated_cost_calculation():
    results = [_make_result("stack-a", 4)]
    cfg = BudgetConfig(cost_per_drifted_resource=10.0, monthly_budget=1000.0)
    out = check_budget(results, cfg)
    assert out.estimated_cost == 40.0


def test_over_budget_flag():
    results = [_make_result("stack-a", 20)]
    cfg = BudgetConfig(cost_per_drifted_resource=10.0, monthly_budget=100.0)
    out = check_budget(results, cfg)
    assert out.over_budget
    assert not out.near_budget


def test_near_budget_flag():
    # 85 USD out of 100 USD budget → over warn_threshold (0.80) but not over budget
    results = [_make_result("stack-a", 17)]
    cfg = BudgetConfig(cost_per_drifted_resource=5.0, monthly_budget=100.0, warn_threshold=0.80)
    out = check_budget(results, cfg)
    assert not out.over_budget
    assert out.near_budget


def test_budget_remaining():
    results = [_make_result("stack-a", 2)]
    cfg = BudgetConfig(cost_per_drifted_resource=10.0, monthly_budget=100.0)
    out = check_budget(results, cfg)
    assert out.budget_remaining == 80.0


def test_multiple_stacks_aggregated():
    results = [
        _make_result("stack-a", 3),
        _make_result("stack-b", 2),
    ]
    cfg = BudgetConfig(cost_per_drifted_resource=10.0, monthly_budget=1000.0)
    out = check_budget(results, cfg)
    assert out.drifted_resource_count == 5
    assert out.estimated_cost == 50.0


# ---------------------------------------------------------------------------
# render_budget_text
# ---------------------------------------------------------------------------

def test_render_text_ok():
    result = BudgetResult(
        estimated_cost=20.0,
        monthly_budget=500.0,
        warn_threshold=0.80,
        over_budget=False,
        near_budget=False,
        drifted_resource_count=4,
    )
    text = render_budget_text(result)
    assert "OK" in text
    assert "$20.00" in text


def test_render_text_over_budget():
    result = BudgetResult(
        estimated_cost=600.0,
        monthly_budget=500.0,
        warn_threshold=0.80,
        over_budget=True,
        near_budget=False,
        drifted_resource_count=120,
    )
    text = render_budget_text(result)
    assert "OVER BUDGET" in text


def test_render_text_near_budget():
    result = BudgetResult(
        estimated_cost=420.0,
        monthly_budget=500.0,
        warn_threshold=0.80,
        over_budget=False,
        near_budget=True,
        drifted_resource_count=84,
    )
    text = render_budget_text(result)
    assert "WARNING" in text
