"""Tests for stackwatch.grouping."""
from __future__ import annotations

import pytest

from stackwatch.drift import DriftResult, DriftedResource
from stackwatch.grouping import (
    GroupingConfig,
    StackGroup,
    build_grouping_report,
    render_grouping_text,
)


def _make_result(stack_name: str, drifted: bool = False, tags: dict | None = None) -> DriftResult:
    resources = []
    if drifted:
        resources = [
            DriftedResource(
                logical_id="Res1",
                resource_type="AWS::S3::Bucket",
                drift_status="MODIFIED",
                expected_properties="{}",
                actual_properties="{\"x\":1}",
            )
        ]
    result = DriftResult(
        stack_name=stack_name,
        drift_status="DRIFTED" if drifted else "IN_SYNC",
        drifted_resources=resources,
    )
    # Attach tags as attribute for grouping (mirrors real usage)
    result.tags = tags or {}
    return result


@pytest.fixture()
def results():
    return [
        _make_result("prod-api", drifted=True, tags={"Environment": "prod"}),
        _make_result("prod-worker", drifted=False, tags={"Environment": "prod"}),
        _make_result("staging-api", drifted=True, tags={"Environment": "staging"}),
        _make_result("dev-api", drifted=False, tags={"Environment": "dev"}),
    ]


def test_invalid_config_raises():
    with pytest.raises(ValueError, match="only one"):
        GroupingConfig(tag_key="Env", prefix_delimiter="-")


def test_group_by_tag(results):
    config = GroupingConfig(tag_key="Environment")
    report = build_grouping_report(results, config)
    names = {g.name for g in report.groups}
    assert names == {"prod", "staging", "dev"}


def test_group_by_prefix(results):
    config = GroupingConfig(prefix_delimiter="-")
    report = build_grouping_report(results, config)
    names = {g.name for g in report.groups}
    assert names == {"prod", "staging", "dev"}


def test_fallback_group_when_no_tag():
    result = _make_result("mystack", tags={})
    config = GroupingConfig(tag_key="Environment", fallback_group="other")
    report = build_grouping_report([result], config)
    assert report.groups[0].name == "other"


def test_drift_rate_per_group(results):
    config = GroupingConfig(tag_key="Environment")
    report = build_grouping_report(results, config)
    prod_group = next(g for g in report.groups if g.name == "prod")
    assert prod_group.total == 2
    assert prod_group.drifted == 1
    assert prod_group.drift_rate == pytest.approx(0.5)


def test_report_totals(results):
    config = GroupingConfig(tag_key="Environment")
    report = build_grouping_report(results, config)
    assert report.total_stacks == 4
    assert report.drifted_stacks == 2


def test_empty_results():
    config = GroupingConfig(fallback_group="none")
    report = build_grouping_report([], config)
    assert report.groups == []
    assert report.total_stacks == 0


def test_render_text_contains_groups(results):
    config = GroupingConfig(tag_key="Environment")
    report = build_grouping_report(results, config)
    text = render_grouping_text(report)
    assert "prod" in text
    assert "staging" in text
    assert "Total:" in text


def test_stack_group_zero_drift_rate():
    group = StackGroup(name="empty")
    assert group.drift_rate == 0.0
