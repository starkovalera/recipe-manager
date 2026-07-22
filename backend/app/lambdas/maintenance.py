import logging
from collections.abc import Mapping
from typing import Any

from app.core.logging import bind_logger
from app.lambdas.sqs import PartialBatchResponse, get_aws_request_id, require_body, require_message_id, require_records
from app.maintenance.constants import MaintenanceProcessingDisposition
from app.maintenance.dispatcher import run_maintenance_operation
from app.queueing.messages import MaintenanceQueueMessage

logger = bind_logger(logging.getLogger(__name__), component="recipes.lambda.maintenance")


def _process_record(record: Mapping[str, Any], *, aws_request_id: str | None) -> tuple[str, bool]:
    message_id = require_message_id(record)
    operation: str | None = None
    try:
        message = MaintenanceQueueMessage.model_validate_json(require_body(record))
        operation = message.operation.value
        result = run_maintenance_operation(message.operation)
    except Exception as error:
        logger.error(
            "Maintenance Lambda record processing failed.",
            aws_request_id=aws_request_id,
            sqs_message_id=message_id,
            operation=operation,
            error_type=type(error).__name__,
        )
        return message_id, False

    logger.info(
        "Maintenance Lambda record processed.",
        aws_request_id=aws_request_id,
        sqs_message_id=message_id,
        operation=operation,
        disposition=result.disposition.value,
        scanned_count=result.scanned_count,
        changed_count=result.changed_count,
        scheduled_count=result.scheduled_count,
        failure_count=result.failure_count,
        anomaly_count=result.anomaly_count,
    )
    return message_id, result.disposition is not MaintenanceProcessingDisposition.RETRYABLE_FAILURE


def handler(event: dict[str, Any], context: object) -> PartialBatchResponse:
    records = require_records(event)
    aws_request_id = get_aws_request_id(context)
    failures = []
    for record in records:
        message_id, succeeded = _process_record(record, aws_request_id=aws_request_id)
        if not succeeded:
            failures.append({"itemIdentifier": message_id})
    return {"batchItemFailures": failures}
