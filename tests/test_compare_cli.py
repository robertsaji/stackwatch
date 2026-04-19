"""Tests for stackwatch.compare_cli."""
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from stackwatch.compare_cli import compare_group


@patch("stackwatch.compare_cli._load")
@patch("stackwatch.compare_cli.compare_snapshots")
@patch("stackwatch.compare_cli.render_compare_text")
def test_diff_exits_zero_no_new_drift(mock_render, mock_compare, mock_load):
    runner = CliRunner()
    mock_compare.return_value = MagicMock(newly_drifted=[], resolved=[])
    mock_render.return_value = "No changes between snapshots."
    result = runner.invoke(compare_group, ["diff", "snap1.json", "snap2.json"])
    assert result.exit_code == 0
    assert "No changes" in result.output


@patch("stackwatch.compare_cli._load")
@patch("stackwatch.compare_cli.compare_snapshots")
@patch("stackwatch.compare_cli.render_compare_text")
def test_diff_exits_nonzero_on_new_drift(mock_render, mock_compare, mock_load):
    runner = CliRunner()
    mock_compare.return_value = MagicMock(newly_drifted=["stack-a"], resolved=[])
    mock_render.return_value = "Newly drifted: stack-a"
    result = runner.invoke(compare_group, ["diff", "snap1.json", "snap2.json"])
    assert result.exit_code == 1


@patch("stackwatch.compare_cli._load")
@patch("stackwatch.compare_cli.compare_snapshots")
def test_summary_output(mock_compare, mock_load):
    runner = CliRunner()
    mock_compare.return_value = MagicMock(
        newly_drifted=["a"], resolved=["b"], still_drifted=["c"]
    )
    result = runner.invoke(compare_group, ["summary", "snap1.json", "snap2.json"])
    assert result.exit_code == 0
    assert "newly_drifted=1" in result.output
    assert "resolved=1" in result.output
    assert "still_drifted=1" in result.output


@patch("stackwatch.compare_cli.Snapshot")
def test_load_raises_on_missing_file(mock_snap_cls):
    runner = CliRunner()
    mock_snap_cls.load.return_value = None
    result = runner.invoke(compare_group, ["diff", "missing.json", "other.json"])
    assert result.exit_code != 0
