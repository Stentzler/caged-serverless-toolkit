# Serverless Toolkit

`serverless-toolkit` is a shared Python library for common utilities used by serverless applications.

Its purpose is to avoid duplicating the same setup across multiple Lambda repositories.

For now, this repository provides:

- Standardized logging for AWS Lambda functions.
- Shared AWS SDK helpers for Lambda functions.

---

## Logging

The logging feature uses AWS Lambda Powertools Logger to generate structured JSON logs.

This helps keep logs consistent across all Lambda functions and makes them easier to search and debug in CloudWatch.

Example usage:

```python
from typing import Any

from serverless_toolkit.observability.lambda_logger import (
    get_lambda_logger,
    inject_lambda_context,
)

logger = get_lambda_logger()


@inject_lambda_context(logger)
def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    logger.info("Starting Lambda execution")

    return {"success": True}
```

The `inject_lambda_context` decorator adds useful Lambda metadata to the logs, such as:

- Function name
- Function ARN
- Memory size
- Request ID
- Cold start information

---

## Environment Variables

The logger can be configured through environment variables:

```env
POWERTOOLS_SERVICE_NAME=
POWERTOOLS_LOG_LEVEL=
POWERTOOLS_LOG_EVENT=
```

### `POWERTOOLS_SERVICE_NAME`

Defines the service name added to each log.

Example:

```env
POWERTOOLS_SERVICE_NAME=check-availability
```

### `POWERTOOLS_LOG_LEVEL`

Defines the minimum log level.

Example:

```env
POWERTOOLS_LOG_LEVEL=INFO
```

Common values:

```text
DEBUG
INFO
WARNING
ERROR
CRITICAL
```

### `POWERTOOLS_LOG_EVENT`

Defines whether the Lambda event should be logged automatically.

Recommended default:

```env
POWERTOOLS_LOG_EVENT=false
```

Keep this disabled by default because events may contain sensitive data.

Logger settings are loaded lazily from the environment and cached for the
process lifetime. Applications that need explicit configuration can inject an
immutable settings object:

```python
from serverless_toolkit.observability.lambda_logger import (
    LoggingSettings,
    get_lambda_logger,
)

settings = LoggingSettings(
    service_name="check-availability",
    log_level="DEBUG",
    log_event=False,
)
logger = get_lambda_logger(settings=settings)
```

---

## DynamoDB

The DynamoDB helper creates a cached `boto3` DynamoDB resource for Lambda
execution environment reuse.

Example usage:

```python
from serverless_toolkit.aws.dynamodb import get_dynamodb_table

registry_table = get_dynamodb_table("downloaded_files_registry")
```

DynamoDB settings are also loaded lazily and cached. Explicit settings can be
provided when a separate resource configuration is required:

```python
from serverless_toolkit.aws.dynamodb import (
    DynamoDBSettings,
    get_dynamodb_table,
)

local_settings = DynamoDBSettings(
    endpoint_url="http://localhost:8000",
    max_pool_connections=10,
)
registry_table = get_dynamodb_table(
    "downloaded_files_registry",
    settings=local_settings,
)
```

Resources with equal settings are reused. Distinct settings receive distinct
cached boto3 resources.

In AWS Lambda, do not configure an endpoint URL. The AWS SDK resolves the
DynamoDB endpoint from the configured region and uses the Lambda execution role
for credentials.

For local DynamoDB, set an endpoint override:

```env
DYNAMODB_ENDPOINT_URL=http://localhost:8000
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=dummy
AWS_SECRET_ACCESS_KEY=dummy
```

### DynamoDB Environment Variables

```env
DYNAMODB_ENDPOINT_URL=
AWS_ENDPOINT_URL_DYNAMODB=
DYNAMODB_MAX_POOL_CONNECTIONS=10
```

### `DYNAMODB_ENDPOINT_URL`

Optional endpoint override for local DynamoDB or custom environments.

Recommended production default: unset.

### `AWS_ENDPOINT_URL_DYNAMODB`

Optional fallback endpoint override, compatible with AWS SDK endpoint naming.

Recommended production default: unset.

### `DYNAMODB_MAX_POOL_CONNECTIONS`

Maximum number of connections kept in the underlying botocore connection pool.

Default:

```env
DYNAMODB_MAX_POOL_CONNECTIONS=10
```

---

## S3

The S3 helper creates a cached low-level boto3 client for Lambda execution
environment reuse. Use the client's managed transfer methods for file uploads.

```python
from serverless_toolkit.aws.s3 import get_s3_client

s3_client = get_s3_client()
s3_client.upload_file("/tmp/archive.7z", "caged-raw-data", "raw/archive.7z")
s3_client.download_file("caged-raw-data", "raw/archive.7z", "/tmp/archive.7z")
```

Both methods use boto3's managed transfer implementation, including multipart
transfers when the configured transfer thresholds require them.

For local S3-compatible services, configure an endpoint override. Leave it
unset in AWS so boto3 uses the configured region and Lambda execution role.

```env
S3_ENDPOINT_URL=http://localhost:4566
AWS_ENDPOINT_URL_S3=
S3_MAX_POOL_CONNECTIONS=10
```

Equal settings reuse the same client. Tests and applications that replace SDK
configuration can call `reset_s3_client_cache()`.

---

## Development

Install dependencies:

```bash
uv sync --all-groups
```

Run tests:

```bash
uv run pytest
```

Run lint:

```bash
uv run ruff check
```
