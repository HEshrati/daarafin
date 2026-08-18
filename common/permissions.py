from rest_framework.exceptions import PermissionDenied


def ensure_maker_checker(*, actor, maker) -> None:
    if actor.pk == maker.pk:
        raise PermissionDenied("ثبت‌کننده نمی‌تواند همان رکورد را تأیید یا رد کند.")
