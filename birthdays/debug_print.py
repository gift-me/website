from django.conf import settings


def debug_print(*args, **kwargs):
    if settings.DEBUG:
        print(*args, **kwargs)
