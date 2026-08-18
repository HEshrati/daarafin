import logging

import sentry_sdk
import structlog


def configure_observability(sentry_dsn: str | None) -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    )
    if sentry_dsn:
        sentry_sdk.init(dsn=sentry_dsn, send_default_pii=False, traces_sample_rate=0.1)
