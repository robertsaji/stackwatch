import pytest
from stackwatch.cost_alert import CostAlertConfig, CostAlertFilter
from stackwatch.drift import DriftResult, DriftedResource


def _make_result(stack_name: str, drifted: bool) -> DriftResult:
    resources = (
        [DriftedResource(logical_id="R", resource_type="AWS::S3::Bucket", status="MODIFIED", properties=["BucketName"])]
        if drifted
        else []
    )
    return DriftResult(stack_name=stack_name, drifted_resources=resources)


@pytest.fixture
def config():
    return CostAlertConfig(
        min_monthly_cost=50.0,
        stack_costs={"expensive": 200.0, "cheap": 10.0},
    )


@pytest.fixture
def filt(config):
    return CostAlertFilter(config)


def test_invalid_min_cost_raises():
    with pytest.raises(ValueError):
        CostAlertConfig(min_monthly_cost=-1.0)


def test_in_sync_result_suppressed(filt):
    r = _make_result("expensive", drifted=False)
    out = filt.evaluate(r)
    assert out.suppressed
    assert "no drift" in out.reason


def test_drifted_above_threshold_not_suppressed(filt):
    r = _make_result("expensive", drifted=True)
    out = filt.evaluate(r)
    assert not out.suppressed
    assert out.cost == 200.0


def test_drifted_below_threshold_suppressed(filt):
    r = _make_result("cheap", drifted=True)
    out = filt.evaluate(r)
    assert out.suppressed
    assert "below threshold" in out.reason


def test_drifted_unknown_cost_suppressed(filt):
    r = _make_result("unknown-stack", drifted=True)
    out = filt.evaluate(r)
    assert out.suppressed
    assert "unknown" in out.reason


def test_zero_threshold_never_suppresses_drifted():
    cfg = CostAlertConfig(min_monthly_cost=0.0)
    f = CostAlertFilter(cfg)
    r = _make_result("any-stack", drifted=True)
    out = f.evaluate(r)
    assert not out.suppressed


def test_apply_returns_all_results(filt):
    results = [_make_result("expensive", True), _make_result("cheap", True), _make_result("x", False)]
    out = filt.apply(results)
    assert len(out) == 3
