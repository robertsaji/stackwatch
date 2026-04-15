"""Unit tests for stackwatch.drift module."""

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from stackwatch.config import AWSConfig
from stackwatch.drift import DriftDetector, DriftResult, DriftedResource


@pytest.fixture()
def aws_config():
    return AWSConfig(region="us-east-1")


@pytest.fixture()
def detector(aws_config):
    with patch("stackwatch.drift.boto3.client"):
        d = DriftDetector(aws_config)
        d._client = MagicMock()
        return d


def _make_waiter():
    w = MagicMock()
    w.wait = MagicMock()
    return w


def test_detect_no_drift(detector):
    detector._client.detect_stack_drift.return_value = {"StackDriftDetectionId": "det-1"}
    detector._client.get_waiter.return_value = _make_waiter()
    detector._client.describe_stack_drift_detection_status.return_value = {
        "StackDriftStatus": "IN_SYNC"
    }

    result = detector.detect("my-stack")

    assert isinstance(result, DriftResult)
    assert result.stack_name == "my-stack"
    assert result.drift_status == "IN_SYNC"
    assert not result.has_drift
    assert result.drifted_resources == []


def test_detect_with_drift(detector):
    detector._client.detect_stack_drift.return_value = {"StackDriftDetectionId": "det-2"}
    detector._client.get_waiter.return_value = _make_waiter()
    detector._client.describe_stack_drift_detection_status.return_value = {
        "StackDriftStatus": "DRIFTED"
    }
    paginator = MagicMock()
    paginator.paginate.return_value = [
        {
            "StackResourceDrifts": [
                {
                    "LogicalResourceId": "MyBucket",
                    "ResourceType": "AWS::S3::Bucket",
                    "StackResourceDriftStatus": "MODIFIED",
                    "ExpectedProperties": '{"BucketName": "foo"}',
                    "ActualProperties": '{"BucketName": "bar"}',
                }
            ]
        }
    ]
    detector._client.get_paginator.return_value = paginator

    result = detector.detect("my-stack")

    assert result.has_drift
    assert len(result.drifted_resources) == 1
    resource = result.drifted_resources[0]
    assert isinstance(resource, DriftedResource)
    assert resource.logical_id == "MyBucket"
    assert resource.drift_status == "MODIFIED"


def test_detect_client_error(detector):
    detector._client.detect_stack_drift.side_effect = ClientError(
        {"Error": {"Code": "ValidationError", "Message": "Stack not found"}},
        "DetectStackDrift",
    )

    result = detector.detect("missing-stack")

    assert result.drift_status == "UNKNOWN"
    assert result.error is not None
    assert not result.has_drift
