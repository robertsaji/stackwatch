"""AWS CloudFormation stack drift detection module."""

import logging
from dataclasses import dataclass, field
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from stackwatch.config import AWSConfig

logger = logging.getLogger(__name__)


@dataclass
class DriftedResource:
    logical_id: str
    resource_type: str
    drift_status: str
    expected_properties: Optional[str] = None
    actual_properties: Optional[str] = None


@dataclass
class DriftResult:
    stack_name: str
    drift_status: str
    drifted_resources: list[DriftedResource] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def has_drift(self) -> bool:
        return self.drift_status == "DRIFTED"


class DriftDetector:
    def __init__(self, aws_config: AWSConfig):
        self._config = aws_config
        self._client = boto3.client(
            "cloudformation",
            region_name=aws_config.region,
            aws_access_key_id=aws_config.access_key_id or None,
            aws_secret_access_key=aws_config.secret_access_key or None,
        )

    def detect(self, stack_name: str) -> DriftResult:
        """Trigger drift detection and return the result."""
        try:
            detection_id = self._start_detection(stack_name)
            self._wait_for_detection(detection_id)
            return self._get_result(stack_name, detection_id)
        except ClientError as exc:
            error_msg = str(exc)
            logger.error("Drift detection failed for %s: %s", stack_name, error_msg)
            return DriftResult(stack_name=stack_name, drift_status="UNKNOWN", error=error_msg)

    def _start_detection(self, stack_name: str) -> str:
        response = self._client.detect_stack_drift(StackName=stack_name)
        return response["StackDriftDetectionId"]

    def _wait_for_detection(self, detection_id: str) -> None:
        waiter = self._client.get_waiter("stack_drift_detection_complete")
        waiter.wait(StackDriftDetectionId=detection_id)

    def _get_result(self, stack_name: str, detection_id: str) -> DriftResult:
        status_resp = self._client.describe_stack_drift_detection_status(
            StackDriftDetectionId=detection_id
        )
        drift_status = status_resp.get("StackDriftStatus", "NOT_CHECKED")
        result = DriftResult(stack_name=stack_name, drift_status=drift_status)

        if result.has_drift:
            paginator = self._client.get_paginator("describe_stack_resource_drifts")
            for page in paginator.paginate(
                StackName=stack_name,
                StackResourceDriftStatusFilters=["MODIFIED", "DELETED"],
            ):
                for r in page.get("StackResourceDrifts", []):
                    result.drifted_resources.append(
                        DriftedResource(
                            logical_id=r["LogicalResourceId"],
                            resource_type=r["ResourceType"],
                            drift_status=r["StackResourceDriftStatus"],
                            expected_properties=r.get("ExpectedProperties"),
                            actual_properties=r.get("ActualProperties"),
                        )
                    )
        return result
