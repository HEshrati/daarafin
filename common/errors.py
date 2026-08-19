from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler as drf_exception_handler


class DomainError(APIException):
    status_code = 400
    default_code = "domain_error"

    def __init__(self, code: str, message: str, *, status_code: int = 400):
        self.status_code = status_code
        super().__init__({"code": code, "message": message}, code=code)


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is not None:
        response.data = {"message": "درخواست قابل پردازش نیست.", "errors": response.data}
    return response
