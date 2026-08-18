from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is not None:
        response.data = {"message": "درخواست قابل پردازش نیست.", "errors": response.data}
    return response
