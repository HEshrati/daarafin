from .models import Medicine


def medicines_for_list(*, search=""):
    from . import services

    return services.medicines_queryset(search=search)


def medicine_prices(medicine: Medicine):
    return medicine.insurance_prices.all().order_by("-letter_miladi_date", "-pk")
