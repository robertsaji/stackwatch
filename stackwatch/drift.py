"""CloudFormation drift detection."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List

import boto3

from stackwatch.config import AWSConfig


@dataclass
class DriftedResource:
    logical_id: str
    resource_type: str
    drift_status: str


@dataclass
class DriftResult:
    stack_name: str
    has_drift: bool
    drifted_resources: List[DriftedResource]
    stack_tags: Dict[str, str] = field(default_factory=dict)


def has_drift(result: DriftResult) -> bool:
    return result.has_drift


class DriftDetector:
    def __init__(self, config: AWSConfig) -> None:
        self._config = config
        self._client = boto3.client(
            "cloudformation",
            region_name=config.region,
        )

    def _get_stack_tags(self, stack_name: str) -> Dict[str, str]:
        try:
            resp = self._client.describe_stacks(StackName=stack_name)
            raw_tags = resp["Stacks"][0].get("Tags", [])
            return {t["Key"]: t["Value"] for t in raw_tags}
        except Exception:
            return {}

    def detect(self, stack_name: str) -> DriftResult:
        detection_id = self._client.detect_stack_drift(StackName=stack_name)[
            "StackDriftDetectionId"
        ]
        waiter = self._client.get_waiter("stack_drift_detection_complete")
        waiter.wait(StackDriftDetectionId=detection_id)

        status_resp = self._client.describe_stack_drift_detection_status(
            StackDriftDetectionId=detection_id
        )
        drift_status = status_resp["StackDriftStatus"]
        has = drift_status == "DRIFTED"

        drifted: List[DriftedResource] = []
        if has:
            paginator = self._client.get_paginator("describe_stack_resource_drifts")
            for page in paginator.paginate(
                StackName=stack_name,
                StackResourceDriftStatusFilters=["MODIFIED", "DELETED"],
            ):
                for r in page["StackResourceDrifts"]:
                    drifted.append(
                        DriftedResource(
                            logical_id=r["LogicalResourceId"],
                            resource_type=r["ResourceType"],
                            drift_status=r["StackResourceDriftStatus"],
                        )
                    )

        tags = self._get_stack_tags(stack_name)
        return DriftResult(
            stack_name=stack_name,
            has_drift=has,
            drifted_resources=drifted,
            stack_tags=tags,
        )

    def detect_all(self, stack_names: List[str]) -> List[DriftResult]:
        return [self.detect(name) for name in stack_names]
