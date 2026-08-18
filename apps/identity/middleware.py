import uuid

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars


class CorrelationIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        clear_contextvars()
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        request.correlation_id = correlation_id
        bind_contextvars(correlation_id=correlation_id)
        structlog.get_logger().info("request.started", method=request.method, path=request.path)
        response = self.get_response(request)
        response["X-Correlation-ID"] = correlation_id
        return response
