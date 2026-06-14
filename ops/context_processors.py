from ops.services import overview_stats


def ops_stats(request):
    if request.path.startswith("/ops") and request.user.is_authenticated and request.user.is_staff:
        return {"stats": overview_stats()}
    return {}
