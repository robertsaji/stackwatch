"""Tests for stackwatch.exporter."""
import json

import pytest

from stackwatch.drift import DriftResult, DriftedResource
from stackwatch.exporter import ExportError, export_html, export_json, export_text
from stackwatch.reporter import build_report


@pytest.fixture()
def simple_report():
    resource = DriftedResource(
        logical_id="Queue",
        resource_type="AWS::SQS::Queue",
        drift_status="MODIFIED",
    )
    results = [
        DriftResult(stack_name="alpha", drifted=True, drifted_resources=[resource]),
        DriftResult(stack_name="beta", drifted=False, drifted_resources=[]),
    ]
    return build_report(results)


def test_export_text_creates_file(tmp_path, simple_report):
    dest = tmp_path / "report.txt"
    out = export_text(simple_report, str(dest))
    assert out.exists()
    content = out.read_text()
    assert "alpha" in content
    assert "DRIFTED" in content


def test_export_text_creates_parent_dirs(tmp_path, simple_report):
    dest = tmp_path / "sub" / "dir" / "report.txt"
    export_text(simple_report, str(dest))
    assert dest.exists()


def test_export_html_creates_file(tmp_path, simple_report):
    dest = tmp_path / "report.html"
    out = export_html(simple_report, str(dest))
    assert out.exists()
    content = out.read_text()
    assert "<table" in content
    assert "alpha" in content


def test_export_json_creates_file(tmp_path, simple_report):
    dest = tmp_path / "report.json"
    out = export_json(simple_report, str(dest))
    assert out.exists()


def test_export_json_valid_structure(tmp_path, simple_report):
    dest = tmp_path / "report.json"
    export_json(simple_report, str(dest))
    data = json.loads(dest.read_text())
    assert data["total_stacks"] == 2
    assert data["drifted_stacks"] == 1
    assert len(data["results"]) == 2
    drifted = next(r for r in data["results"] if r["stack_name"] == "alpha")
    assert drifted["drifted"] is True
    assert drifted["drifted_resources"][0]["logical_id"] == "Queue"


def test_export_error_on_bad_path(simple_report):
    with pytest.raises(ExportError):
        export_text(simple_report, "/proc/no_permission/report.txt")
