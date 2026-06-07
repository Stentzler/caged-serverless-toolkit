# Serverless Toolkit

`serverless-toolkit` is a shared Python library for common utilities used by serverless applications.

Its purpose is to avoid duplicating the same setup across multiple Lambda repositories.

For now, this repository only provides:

- Standardized logging for AWS Lambda functions.

---

## Logging

The logging feature uses AWS Lambda Powertools Logger to generate structured JSON logs.

This helps keep logs consistent across all Lambda functions and makes them easier to search and debug in CloudWatch.

Example usage:

```python
from typing import Any

from serverless_toolkit.observability import (
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